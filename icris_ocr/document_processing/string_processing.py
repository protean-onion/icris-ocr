"""
This module defines functions used for cleaning extracted data.

"""

import re

sort_regex = re.compile(r'\d{1,2}')

regex_presentors_name = re.compile(r'(?<=Name[;:\s!])[\s\S]*(?=Address)')
regex_presentors_address = re.compile(r'(?<=Address[;:\s!])[\s\S]*(?=Tel[;:\s])')
regex_presentors_telephone = re.compile(r'(?<=Tel[;:\s!])[\s\S!il|soO]*(?=Fax[;:\s])')
regex_presentors_fax = re.compile(r'(?<=Fax[:\s;!])[\s\S]*(?=E(m|-m)ail)')
regex_presentors_email = re.compile(r'(?<=Email[:;\s!])[\s\S]*@[\s\S]*\.\w{1,}')

def clean_chinese(string: str):
    """Remove Chinese characters and return the cleaned string"""

    string = re.sub(f'[^a-zA-Z,\-0-9\s.]', '', string)
    return string

def check_empty(string: str, delimiter: str = ' '):
    """Check if string represents dirty data"""
    
    string_list = string.split(delimiter)
    check = 0

    for string in string_list:
        if len(string) < 3:
            check += 1
    
    if check == len(string_list):
        string = 'None'
    else:
        string = ' '.join(string_list)

    return string

def search_string(regex: re.compile, input_string: str):
    """Construct a regular expression and match it in the passed string"""

    match = regex.search(input_string)

    try:
        string = match.group().strip()
        return string
    except:
        return 'None'

def separate_text(
    string: str,
    nSpaces: int =3,
    data_type: str = None,
    numbers: bool = False,
    save: bool = False):
    """Separate different names in the same column delimited by two or more newline characters"""

    string = clean_chinese(string.replace('\n', ' ').strip())
    string = re.sub(r'\s{%s,}' % nSpaces, ';', string)

    string_list = [string for string in string.split(';') if string != '']

    if data_type == 'letter':
        string_list = [clean_alphabet(string) if ('nil' not in string.lower()) else 'None' for string in string_list]
    elif data_type == 'number':
        string_list = [clean_number(number, data_type = 'number') if ('nil' not in number.lower()) else 'None' for number in string_list]

    string = ';'.join(string_list)

    return string if string != '' else 'None'

def clean_alphabet(string: str):
    """Remove all non-alphabet characters and returned the cleaned string"""
    cleaned = re.sub(r'[^A-Za-z \n]', '', string)
    cleaned = cleaned.replace('\n', ' ').replace('  ', ' ')
    cleaned_list = cleaned.split()
    
    check_empty = 0
    for string in cleaned_list:
        if len(string) < 3:
            check_empty += 1

    if check_empty == len(cleaned_list):
        cleaned_list = ['None']

    cleaned = ' '.join(cleaned_list)

    return cleaned

def clean_number(
    string: str,
    data_type: str = 'number'):
    """Remove all non-digit characters and return the cleaned string"""

    try:
        string = string[:string.index('.')] # Convert to non-decimal number
    except:
        pass

    cleaned = re.sub(r'sS', '5', re.sub(r'oO', '0', re.sub(r'[\[\]Iil!|]', '1', string)))
    cleaned = re.sub(r'[^0-9]', '', cleaned)

    if data_type == 'contact':
        if cleaned.startswith('852'):
            cleaned = cleaned[3:]
        elif cleaned.startswith('0852'):
            cleaned = cleaned[4:]

        if len(cleaned) >= 8:
            cleaned = cleaned[:8]
        else:
            cleaned = 'None'

    elif data_type == 'number':
        cleaned = re.sub(r'[^0-9]', '', cleaned)

    return cleaned if cleaned != '' and cleaned != '()' else 'None'

def clean_hkid(string: str):
    """Check if HKID was detected correctly and reformat
    the detected string"""

    cleaned = re.sub(r'[^A-Z0-9]', '', string)
    cleaned_list = [letter for letter in cleaned]
    cleaned_list.insert(-1, '(')
    cleaned_list.append(')')
    cleaned = ''.join(cleaned_list)

    return cleaned if len(cleaned) > 7 else 'None'

def clean_single_character(string: str, data_type: str = 'letter'):
    """Clean a string that is expected to contain only a character"""

    if data_type == 'letter':
        cleaned = re.sub(r'[^A-Z]', '', string.strip())[:1]
    elif data_type == 'number':
        cleaned = re.sub(r'sS', '5', re.sub(r'oO', '0', re.sub(r'[\[\]Iil!|]', '1', string)))
        cleaned = re.sub(r'[^0-9]', '', cleaned)[:1]
    return cleaned
