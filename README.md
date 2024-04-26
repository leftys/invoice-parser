# Invoice parser

For py3.11

```
python cli.py --startid 6 --openai_api_key='[take from .env]' \
/home/lefty/Documents/Ucto_Itol/Ucto\ 2024\ doklady/*.pdf  |tee faktury.csv; \
iconv -f utf8 -t cp1250 <faktury.csv >faktury_cp1250.csv
```
