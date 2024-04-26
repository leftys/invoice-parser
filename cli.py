from typing import Dict
import click
import datetime
import csv
import warnings
import cachetools
import requests
import pickle
from extracter_agent import ExtracterAgent


@click.command()
@click.argument('pdf_files', nargs=-1, type=click.Path(exists=True))
@click.option('--openai_api_key')
@click.option('--cache', is_flag=True, help='Use cache from last run -- for testing')
@click.option('--startid', type=int, default=1)
def convert_pdfs_to_csv(pdf_files, openai_api_key, cache, startid):
    if cache:
        result = pickle.load(open('result.pkl', 'rb')) # Use cache from last run -- for testing
    else:
        agent = ExtracterAgent(openai_api_key)
        files = [open(pdf_file, 'rb') for pdf_file in pdf_files]
        warnings.filterwarnings("ignore")
        result = agent.run_agent(files)
        for file in files:
            file.close()

        pickle.dump(result, open('result.pkl', 'wb'))

    result = sorted(result, key=lambda invoice: invoice.date)
    # Output csv with format of Stereo accounting SW for invoices
    key_map = {
        'doklad': 'Doklad',
        'cislo': 'Číslo dokladu',
        'agenda': 'Agenda',
        'rada': 'Řada dokladu',
        'druh': 'Druh',
        # 'id': 'Párovací znak',
        'date': 'Okamžik vystavení',
        'date_a': 'Okamžik uskutečnění',
        'date_s': 'Datum splatnosti',
        'description': 'Text',
        'tax_rate': 'Sazba DPH',
        'total_amount': 'Celkem v cizí měně',
        'total_czk': 'Celkem',
        'currency': 'Měna',
        'supplier_name': 'Název firmy',
        'invoice_language': 'Jazyk faktury',
        'variabilni_symbol': 'Variabilní symbol',
        'rate': 'Kurz',
        'dal': 'Dal',
        'ma dati': 'Má dáti',
        'type': 'Typ dokladu',
        'id': 'Související doklad',
    }
    writer = csv.DictWriter(click.get_text_stream('stdout'), fieldnames=list(key_map.values()), delimiter = ';')
    writer.writeheader()
    cislo = startid

    for invoice in result:
        invoice_dict = invoice.dict()
        invoice_dict['agenda'] = 'PF'
        invoice_dict['rada'] = 'pf'
        invoice_dict['druh'] = 'NS'
        invoice_dict['dal'] = '321'
        invoice_dict['ma dati'] = '518v' if invoice_dict['invoice_language'] == 'Czech' else '518o'
        date_iso = invoice_dict['date']
        invoice_dict['date'] = datetime.datetime.strptime(invoice_dict['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        invoice_dict['date_a'] = invoice_dict['date']
        invoice_dict['date_s'] = invoice_dict['date']
        invoice_dict['rate'] = 1 if invoice_dict['currency'] == 'CZK' else fx_rate_at_date(invoice_dict['currency'], 'CZK', date_iso)
        invoice_dict['total_czk'] = round(invoice_dict['total_amount'] * invoice_dict['rate'], 2)
        invoice_dict['type'] = 'F'
        invoice_dict['doklad'] = f'pf{cislo:0>4d}'
        invoice_dict['cislo'] = f'{cislo:0>4d}'
        if invoice_dict['currency'] == 'CZK':
            invoice_dict['currency'] = 'Kč'
        cislo += 1
        if invoice_dict['variabilni_symbol'] is None:
            invoice_dict['variabilni_symbol'] = '0'
        invoice_dict = {key_map.get(key, key): value for key, value in invoice_dict.items()}
        writer.writerow(localize_floats(invoice_dict))

@cachetools.cached(cachetools.TTLCache(maxsize=128, ttl=10))
def fx_rate_at_date(base: str, dest: str, date: str) -> float:
    '''
    Convert forex rates using some daily rate.
    That rate can be even few days old on Weekends/holidays.
    Params base and dest have to be uppercase (eg. EUR)
    '''
    # 5000 requests/mo ~= 1 req every 10m
    api_key = 'c2aefee703552202e2e8366c92bd3efe'
    resp = requests.get(f'https://api.currencyscoop.com/v1/historical?date={date}&base={base}&symbols={dest}&api_key={api_key}')
    resp.raise_for_status()
    json = resp.json()
    # API resonse is like:
    # {"meta":{"code":200,"disclaimer":"Usage subject to terms: https:\/\/currencyscoop.com\/terms"},"response":{"date":"2021-05-24T18:23:41Z","base":"CZK","rates":{"USD":0.04807699}}}
    rate = json['response']['rates'][dest]
    return rate

def localize_floats(record: Dict):
    ''' Replace decimal dots with decimal commas '''
    return {
        key: str(el).replace('.', ',') if isinstance(el, float) else el
        for key, el in record.items()
    }

# def convert_utf8_to_cp1250(input_file, output_file):
#     with codecs.open(input_file, 'r', 'utf-8') as infile:
#         contents = infile.read()

#     with codecs.open(output_file, 'w', 'cp1250') as outfile:
#         outfile.write(contents)

if __name__ == '__main__':
    convert_pdfs_to_csv()
