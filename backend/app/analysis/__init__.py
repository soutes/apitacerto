"""Aba Dados estatisticos (spec secao 9) -- calculo OFFLINE.

Importa numpy/scipy/pandas/statsmodels (grupo de dependencias 'analysis').
Nada daqui pode ser importado pelo caminho da request (app/main.py): a API
so le o JSON pronto em stat_reports, pra funcao serverless da Vercel ficar
leve. Quem chama isto e scripts/compute_stats.py (e o fim do scraping).
"""
