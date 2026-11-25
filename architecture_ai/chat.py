"""Interactive local architecture assistant for repository URLs and folders."""
import json
import copy
import os
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from architecture_ai.analyzer import analyze_with_local_model, source_records_for_query
from architecture_ai.ollama_provider import LocalModelError
from architecture_ai.render import generate_report
from architecture_ai.scope import classify_question
from architecture_ai.visual import build_visual
from architecture_ai.retrieval import index_repositories

DEFAULT_QUESTION = ('Identifique os serviços, suas responsabilidades, interfaces e comunicações. '
                    'Inclua serviços isolados e destinos não identificados, com evidências. '
                    'Distinga fatos confirmados, inferências e informações desconhecidas.')


def heading(label):
    color = sys.stdout.isatty() and not os.environ.get('NO_COLOR')
    return ('\033[1;36m' + label + '\033[0m') if color else label


def prepare_sources(sources, clone_root):
    repositories = []
    for source in sources:
        parsed = urlparse(source)
        if parsed.scheme in ('https', 'http'):
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValueError('Use uma URL HTTPS sem usuário, senha, parâmetros ou fragmento.')
            name = Path(parsed.path.rstrip('/')).name
            if name.endswith('.git'):
                name = name[:-4]
            if not name or name in ('.', '..'):
                raise ValueError('Não foi possível identificar o nome do repositório.')
            target = clone_root / name
            if target.exists() or any(p.name == name for p in repositories):
                raise ValueError('Nomes de repositórios duplicados: ' + name)
            print('Baixando {}...'.format(parsed.hostname + parsed.path), flush=True)
            try:
                subprocess.run(['git', 'clone', '--quiet', '--', source, str(target)], check=True)
            except subprocess.CalledProcessError as error:
                raise ValueError('Não foi possível clonar o repositório. Confira URL e autenticação Git.') from error
            repositories.append(target)
        elif not parsed.scheme:
            path = Path(source).expanduser().resolve()
            if not path.is_dir():
                raise ValueError('Pasta não encontrada: ' + source)
            if any(p.name == path.name for p in repositories):
                raise ValueError('Nomes de repositórios duplicados: ' + path.name)
            repositories.append(path)
        else:
            raise ValueError('Use uma URL HTTPS ou caminho de pasta local.')
    return repositories


def print_result(result, warnings):
    labels = {'confirmed': 'confirmado', 'inferred': 'inferido', 'unknown': 'desconhecido'}
    print('\n' + heading('◆ COMPONENTES'))
    for component in result.get('components', []):
        print('- {}: {} [{}]'.format(component.get('name'), component.get('responsibility'), labels.get(component.get('certainty'), 'desconhecido')))
    print('\n' + heading('◆ COMUNICAÇÕES'))
    if not result.get('relationships'):
        print('- Nenhuma ligação foi identificada nas evidências fornecidas.')
    for relation in result.get('relationships', []):
        print('- {} → {}: {} {} [{}]'.format(relation.get('source'), relation.get('target'), relation.get('protocol'), relation.get('operation'), labels.get(relation.get('certainty'), 'desconhecido')))
    for unknown in result.get('unknowns', []):
        print('- Informação desconhecida: ' + str(unknown))
    if warnings:
        print('\nAtenção: {} citações precisam de revisão; consulte o JSON.'.format(len(warnings)))


def run_chat(sources, output, prompt_version):
    print(heading('╭─ Architecture AI ─────────────────────────────╮'))
    print('│  Repositórios, evidências e arquitetura local  │')
    print(heading('╰────────────────────────────────────────────────╯'))
    if not sources:
        print('Informe um caminho local ou URL HTTPS por linha. Linha vazia inicia a análise.')
        sources = []
        while True:
            line = input('Repositório: ').strip()
            if not line:
                break
            sources.append(line)
    if not sources:
        print('Nenhum repositório informado.')
        return
    session_root = Path('.architecture/sessions').resolve()
    session_root.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='session-', dir=str(session_root)))
    repositories = prepare_sources(sources, root)
    database = root / 'evidence.sqlite'
    print('Preparando índice local de evidências...')
    count = index_repositories(repositories, database)
    output.mkdir(parents=True, exist_ok=True)
    outputs = generate_report(repositories, output)
    print('{} trechos indexados. Diagrama estático: {}'.format(count, outputs['svg']))
    print('Digite sua pergunta • Enter: visão geral • /abrir: diagrama • sair: encerrar')
    history = []
    visual_ready = False
    while True:
        try:
            question = input('\nVocê: ').strip()
        except EOFError:
            print('\nAté logo.')
            break
        if question.lower() in ('sair', 'exit', 'quit'):
            break
        if question.lower() == '/abrir':
            visual = output / 'arquitetura.html'
            if visual_ready and visual.exists():
                webbrowser.open(visual.as_uri())
                print('Abrindo {}'.format(visual))
            else:
                print('Faça uma análise primeiro para criar o diagrama.')
            continue
        default_view = not question
        question = question or DEFAULT_QUESTION
        if not default_view:
            print('Verificando a pergunta...', flush=True)
            try:
                scope = classify_question(question, history)
            except LocalModelError as error:
                print(str(error))
                continue
            if scope == 'out_of_scope':
                print('Posso ajudar com arquitetura de software, repositórios, código e tecnologias relacionadas.')
                continue
            if scope == 'unclear':
                print('Pode explicar como sua pergunta se relaciona aos repositórios ou à arquitetura?')
                continue
        print('Consultando o modelo local; isso pode levar alguns minutos...', flush=True)
        try:
            analysis, warnings = analyze_with_local_model(question, repositories, database, prompt_version, history=history)
        except LocalModelError as error:
            print('Não foi possível concluir a análise: {}'.format(error))
            continue
        raw_analysis = copy.deepcopy(analysis)
        adjustments = []
        for relation in analysis.get('relationships', []):
            if relation.get('certainty') == 'confirmed':
                relation['certainty'] = 'inferred'
                adjustments.append('A relação {} → {} foi marcada como inferida: configuração pode variar em execução.'.format(
                    relation.get('source'), relation.get('target')))
        payload = {'model': os.environ.get('OLLAMA_MODEL', 'qwen3:8b'), 'prompt_version': prompt_version,
                   'question': question, 'analysis': analysis, 'model_raw_analysis': raw_analysis, 'citation_warnings': warnings,
                   'certainty_adjustments': adjustments}
        result_path = output / 'llm-analysis.json'
        result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        visual_path = output / 'arquitetura.html'
        records = source_records_for_query(question, repositories, database)
        build_visual(analysis, repositories, records, visual_path)
        visual_ready = True
        history.append({'question': question, 'summary': [
            {'name': c.get('name'), 'responsibility': c.get('responsibility')} for c in analysis.get('components', [])
        ]})
        print_result(analysis, warnings)
        for adjustment in adjustments:
            print('Nota: ' + adjustment)
        print('\nEvidências e resposta completa: {}'.format(result_path))
        print('Visão no navegador: {}'.format(visual_path))
        print('Diagrama SVG: {} | Mermaid: {}'.format(outputs['svg'], outputs['mermaid']))
