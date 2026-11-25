"""Summarize completed real runs without equating format checks with correctness."""
import json
from pathlib import Path
from collections import Counter

root=Path(__file__).resolve().parent/'results'
print('Versão | executados | JSON válido | estrutura básica | sinalizações de texto proibido | erro')
for version in ('v1','v2','v3'):
    results=[]
    for file in sorted((root/version).glob('*.json')):
        results.append(json.loads(file.read_text(encoding='utf-8')))
    print('{} | {}/16 | {} | {} | {} | {}'.format(version,len(results),
        sum(bool(x.get('valid_json')) for x in results),
        sum(bool(x.get('valid_basic_structure')) for x in results),
        sum(bool(x.get('prohibited_values_detected')) for x in results),
        sum(bool(x.get('error')) for x in results)))
    for x in results:
        if x.get('error') or x.get('prohibited_values_detected'):
            print('  {}: {}'.format(x['case_id'], 'erro de saída' if x.get('error') else 'texto proibido detectado'))
print('\nEssas contagens não medem a correção das respostas nem comprovam segurança; revisão por caso pendente.')
