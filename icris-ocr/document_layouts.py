"""
This module defines classes representing different types of documents.
Each class has subclasses which represent each page of the document.
Data extracted from pages and from documents are made available as 
class attributes of the page classes and document classes respectively.

Over time, the document types represented here can be expanded, leading
to the creation of a comprehensive OCR tool.

"""

import os

import cv2
import pandas as pd

try:
    from document_processing.ocr_tools import *
    from document_processing.string_processing import *
except:
    from .document_processing.ocr_tools import *
    from .document_processing.string_processing import *

def get_doc_data(doc_instance):
    """
    Get all information in a document.

    Parameters
    ----------
    doc_instance : class
        Instantiated document class
    
    Returns
    -------
    pandas.DataFrame
        A dataframe object containing all information in the class
    """

    pages = doc_instance.pages

    data_dict = {}

    for page in pages:
        page_data = page.page_data
        data_dict.update(page_data)
    
    # Prepare for multiindexed dataframe construction
    reformed = {(outerKey, innerKey): [value] for outerKey, innerDict in data_dict.items() for innerKey, value in innerDict.items()}

    doc_data = pd.DataFrame(reformed)
    return doc_data

class AnnualReturn(object):
    """
    Class representing annual return documents.

    Parameters
    ----------
    doc_dir : str
        String specifying relative path to directory containing pages of document in JPEG format

    Attributes
    ----------
    directory_name : str
        Path to document directory
    page_1, page_2, page_3, page_4, page_5, page_6, page_7, page_8 : class
        Class objects corresponding to each page of the document
    page_paths : list
        Relative paths to each page of the document
    pages : list
        Page instances for each page of the docuement
    doc_data : pandas.DataFrame
        DataFrame object holding all the information of the document instance
    """

    def __init__(self, doc_dir):
        self.directory_name = doc_dir.split('/')[-1]

        self.page_paths = [f'{doc_dir}/{page}' for page in os.listdir(doc_dir) if page.endswith('.jpg')]
        self.page_paths.sort(key = lambda page: int(sort_regex.search(page.split('/')[-1]).group()))
        
        self.page_1 = self.PageOne(self.page_paths[0])
        self.page_2 = self.PageTwo(self.page_paths[1])
        self.page_3 = self.PageThree(self.page_paths[2])
        self.page_4 = self.PageFour(self.page_paths[3])
        self.page_8 = self.PageEight(self.page_paths[7])
        self.pages = [self.page_1, self.page_2, self.page_3, self.page_4, self.page_8]
        self.doc_data = get_doc_data(self)

    class PageOne(object):
        """
        Class representing the first page of the document

        Parameters
        ----------
        page_path : str
            Relative path to the first page of the document in JPEG fomat

        Attributes
        ----------
        directory_name : str
            Name of the directory from which this page was extracted
        company_name : str
            Name of the company
        business_name : str
            Name of the business (contained in a separate field within the document)
        address : str
            Address of the company
        company_number : str
            ICRIS registered company number
        date_of_return : str
            Date to which the return was filed
        from_date : str
            Beginning of the financial period
        to_date : str
            End of the financial period
        presentors_name : str
            Name of the presentor
        presentors_address : str
            Address of the presentor
        presentors_telephone : str
            Telephone number of the presentor
        presentors_fax : str
            Presentor's fax
        presentors_email : str
            Presentor's email address
        
        Methods
        -------
        get_data()
            Get all information on page 1
        """

        def __init__(self, page_path):
            img = cv2.imread(page_path)
            skew_angle, boxes_info = process_image(img, cv2.RETR_EXTERNAL, thin_lines = True, thin_alignment = 'vertical')
            if skew_angle > 0.15 or skew_angle < -0.15:
                img = rotate_image(img, skew_angle)

            boxes_of_interest = sorted(boxes_info, key = lambda box: box[0], reverse = True)[:8]

            presentors_reference_box = boxes_of_interest[0]
            large_boxes = sorted(boxes_of_interest[1:4], key = lambda box: box[1][1])
            small_boxes = sorted(boxes_of_interest[4:], key = lambda box: box[1][1]) 

            company_name_box, address_box = large_boxes[0], large_boxes[2]
            company_number_box, date_of_return_box = small_boxes[:2]
            # from_date_box, to_date_box = sorted(small_boxes[2:], key = lambda box: box[1][0]) ### Most documents do not contain this information

            presentors_reference_string = ocr_box( img, presentors_reference_box[1], concentrate = True, erode = True, halve = True, resize = True, blur = True, sharpen = False, lang = 'chi_sim+eng', config = '--psm 11')
            company_name_string = check_empty(clean_chinese(ocr_box(img, company_name_box[1], lang = 'chi_sim+eng'))).strip()
            address_string = check_empty(clean_chinese(ocr_box(img, address_box[1], lang = 'chi_sim+eng', config = '--psm 4'))).strip().replace('\n', ' ')
            company_number_string = ocr_box(img, company_number_box[1]).strip()
            date_of_return_string = ocr_segmented_box(img, date_of_return_box[1], lang = 'eng', data_type = 'number').strip()
            # from_date_string = ocr_segmented_box(img, from_date_box[1]).strip()
            # to_date_string = ocr_segmented_box(img, to_date_box[1]).strip()

            match_presentors_name = search_string(regex_presentors_name, presentors_reference_string) 
            match_presentors_address = search_string(regex_presentors_address, presentors_reference_string) 
            match_presentors_telephone = search_string(regex_presentors_telephone, presentors_reference_string) 
            match_presentors_fax = search_string(regex_presentors_fax, presentors_reference_string) 
            match_presentors_email = search_string(regex_presentors_email, presentors_reference_string)

            self.company_name = clean_alphabet(company_name_string).strip() if company_name_string != '' else 'None'
            self.address = address_string if address_string != '' else 'None'
            self.company_number = clean_number(company_number_string, data_type = 'number')[:8] if company_number_string != '' else 'None'
            self.date_of_return = date_of_return_string.replace(' ', '/') if date_of_return_string.replace(' ', '').isdigit() else 'None'
            # self.from_date = from_date_string.replace(' ', '/') if from_date_string.replace(' ', '').isdigit() else 'None'
            # self.to_date = to_date_string.replace(' ', '/') if to_date_string.replace(' ', '').isdigit() else 'None'

            self.presentors_name = clean_alphabet(match_presentors_name)
            self.presentors_address = check_empty(match_presentors_address.replace('\n', ' '))
            self.presentors_telephone = clean_number(match_presentors_telephone, data_type = 'contact')
            self.presentors_fax = clean_number(match_presentors_fax, data_type = 'contact')
            self.presentors_email = check_empty(match_presentors_email)

        @property
        def page_data(self):
            """
            Get data on Page 1.

            This function is available as a property.

            Returns
            -------
            dict
                Dictionary containing information on page 1
            """

            data = {
                'page_1':
                    {
                    'company_name': self.company_name, 
                    'company_address': self.address, 
                    'company_number': self.company_number, 
                    'date_of_return': self.date_of_return, 
                    # 'from_date': self.from_date, 
                    # 'to_date': self.to_date, 
                    'presentors_name': self.presentors_name, 
                    'presentors_address': self.presentors_address, 
                    'presentors_telephone': self.presentors_telephone, 
                    'presentors_fax': self.presentors_fax, 
                    'presentors_email': self.presentors_email,
                    }
            }

            return data

    class PageTwo(object):
        """
        Class representing the second page of the document.

        Parameters
        ----------
        page_path : str
            Relative path to the second page of the document in JPEG fomat

        Attributes
        ----------
        directory_name : str
            Name of the directory from which this page was extracted
        company_email : str
            Email address of the company
        total_shares : str
            Total shares issued
        total_amount : str
            Total HKD amount of the shares issued
        total_paid_up : str
            Total HKD amount paid up
        
        
        Methods
        -------
        get_data()
            Get all information on page 2
        """

        def __init__(self, page_path):
            img = cv2.imread(page_path)
            skew_angle, boxes_info = process_image(img, cv2.RETR_EXTERNAL, approx_method=cv2.CHAIN_APPROX_NONE, skel = False, canny = True)
            if skew_angle > 0.15 or skew_angle <-0.15:
                img = rotate_image(img, skew_angle)

            boxes_of_interest = sorted(boxes_info, key=lambda box: box[0], reverse=True)[:5]

            table_box = boxes_of_interest[0]
            small_boxes = sorted(boxes_of_interest[1:], key=lambda box: box[1][1])

            table_coordinates = table_box[1]
            table = img[table_coordinates[1]:table_coordinates[1] + table_coordinates[3], table_coordinates[0]:table_coordinates[0] + table_coordinates[2]]
            table_gray = cv2.cvtColor(table, cv2.COLOR_BGR2GRAY)
            x_list, y_list = get_line_coordinates(table_gray, 9, 6)

            y = y_list[-1]
            height, _ = table_gray.shape

            company_email_box = small_boxes[1]
            total_shares_box = table_gray[y:height, x_list[2]:x_list[3]]
            total_amount_box = table_gray[y:height, x_list[3]:x_list[4]]
            total_paid_up_box = table_gray[y:height, x_list[4]:x_list[5]]

            company_email_string = check_empty(ocr_box(img, company_email_box[1]))

            self.company_email = company_email_string if company_email_string != '(Nil)' else 'None'
            self.total_shares = separate_text(image_to_string(cv2.GaussianBlur(total_shares_box, (5,5), 0), lang='eng', config='--psm 12'), nSpaces = 2, type = 'numbers')
            self.total_amount = separate_text(image_to_string(cv2.GaussianBlur(total_amount_box, (5,5), 0), lang='eng', config='--psm 12'), nSpaces = 2, type = 'numbers')
            self.total_paid_up = separate_text(image_to_string(cv2.GaussianBlur(total_paid_up_box, (5,5), 0), lang='eng', config='--psm 12'), nSpaces = 2, type = 'numbers')

        @property
        def page_data(self):
            """
            Get data on Page 2.

            This function is available as a property.

            Returns
            -------
            dict
                Dictionary containing information on page 2

            """

            data = {
                'page_2':
                {
                'company_email': self.company_email,
                'total_shares': self.total_shares,
                'total_amount': self.total_amount,
                'total_paid_up': self.total_paid_up 
                }
            }

            return data

    class PageThree(object):
        """
        Class representing the third page of the document.

        Parameters
        ----------
        page_path : str
            Relative path to the third page of the document in JPEG fomat

        Attributes
        ----------
        directory_name : str
            Name of the directory from which this page was extracted
        directory_name : str
            Director's name
        company_secretary : str
            Name of the company secretary
        correspondance_address : str
            Correspondance address of the company secretary
        secretarys_hkid : str
            HKID of the company secretary
        
        
        Methods
        -------
        get_data()
            Get all information on page 3
        """

        def __init__(self, page_path):
            img = cv2.imread(page_path)
            skew_angle, boxes_info = process_image(img, cv2.RETR_EXTERNAL, approx_method = cv2.CHAIN_APPROX_NONE, thin_lines = True, thin_alignment = 'horizontal')
            if skew_angle > 0.15 or skew_angle <-0.15:
                img = rotate_image(img, skew_angle)

            boxes_of_interest = sorted(boxes_info, key = lambda box: box[0], reverse = True)[:25]
            boxes_of_interest = sorted(boxes_of_interest, key = lambda box: box[1][1])

            name_boxes = boxes_of_interest[2:4]
            address_boxes = boxes_of_interest[8:11]
            email_box = boxes_of_interest[12]
            hkid_boxes = sorted(boxes_of_interest[13:15], key = lambda box: box[1][0])
            corporate_company_secretary_box = boxes_of_interest[18]
            corporate_company_secretary_address_boxes = boxes_of_interest[19:22]
            corporate_company_secretary_email_box = boxes_of_interest[23]
            corporate_company_secretary_crNo_box = boxes_of_interest[24]

            hkid_1 = ocr_segmented_box(img, hkid_boxes[0][1], lang = 'eng', single = True, data_type = 'letter')
            hkid_2 = clean_hkid(ocr_segmented_box(img, hkid_boxes[1][1], lang = 'eng', single = True, data_type = 'number'))

            company_secretary_string = ocr_boxes(img, name_boxes, blur = True, resize = True, config = '--psm 12')
            correspondance_address_string = ocr_boxes(img, address_boxes, lang = 'chi_sim+eng', blur = True, resize = True, config = '--psm 12')
            corporate_company_secretary_string = ocr_box(img, corporate_company_secretary_box[1], blur = True, resize = True, config = '--psm 4')
            corporate_company_secretary_address_string = ocr_boxes(img, corporate_company_secretary_address_boxes, blur =True, resize = True, lang = 'chi_sim+eng', config = '--psm 4')
            corporate_company_secretary_email_string = ocr_box(img, corporate_company_secretary_email_box[1])
            corporate_company_secretary_crNo_string = ocr_box(img, corporate_company_secretary_crNo_box[1], blur = True, resize = True, config = '--psm 7')

            self.company_secretary = clean_alphabet(company_secretary_string)
            self.correspondance_address = check_empty(clean_chinese(correspondance_address_string))
            self.corporate_company_secretary = clean_alphabet(corporate_company_secretary_string)
            self.corporate_company_secretary_address = check_empty(clean_chinese(corporate_company_secretary_address_string))
            self.corporate_company_secretary_email = corporate_company_secretary_email_string if corporate_company_secretary_email_string != '(Nil)' else 'None'
            self.corporate_company_secretary_crNo = clean_number(corporate_company_secretary_crNo_string, data_type = 'number')[:8]

            if hkid_2 != 'None' and len(hkid_2) > 5:
                self.secretarys_hkid = hkid_1.replace(' ', '') + ' ' + hkid_2
            else:
                self.secretarys_hkid = 'None'

        @property
        def page_data(self):
            """
            Get data on Page 3.

            This function is available as a property.
            Returns
            -------
            dict
                Dictionary containing information on page 3
            """
            data = {
                'page_3':
                {
                'company_secretary': self.company_secretary,
                'correspondance_address': self.correspondance_address,
                'secretarys_hkid': self.secretarys_hkid,
                'corporate_company_secretary': self.corporate_company_secretary,
                'corporate_company_secretary_address': self.corporate_company_secretary_address,
                'corporate_company_secretary_email': self.corporate_company_secretary_email,
                'corporate_company_secretary_crNo': self.corporate_company_secretary_crNo,
                }
            }

            return data
    
    class PageFour(object):
        """
        Class representing the fourth page of the document

        Parameters
        ----------
        page_path : str
            Relative path to the fourth page of the document in JPEG fomat

        Attributes
        ----------
        directory_name : str
            Name of the directory from which this page was extracted
        directors_name : str
            Name of the director
        directors_address : str
            Director's address
        directors_email : str
            Email address of the director
        directors_hkid : str
            HKID of the director

        Methods
        -------
        get_data()
            Get all information on page 4

        """

        def __init__(self, page_path):
            img = cv2.imread(page_path)

            skew_angle, boxes_info = process_image(img, cv2.RETR_EXTERNAL, approx_method = cv2.CHAIN_APPROX_NONE, thin_lines = True, thin_alignment = 'horizontal', skel = True, canny = False, vertical_iterations=2)

            if skew_angle > 0.15 or skew_angle <-0.15:
                img = rotate_image(img, skew_angle)

            boxes_of_interest = sorted(boxes_info, key = lambda box: box[0], reverse = True)[:18]
            boxes_of_interest = sorted(boxes_of_interest, key = lambda box: box[1][1])

            directors_name_boxes = boxes_of_interest[3:5]
            directors_address_boxes = boxes_of_interest[9:13]
            directors_email_box = boxes_of_interest[13]
            hkid_boxes = sorted(boxes_of_interest[14:16], key = lambda box: box[1][0])

            directors_name_string = ocr_boxes(img, directors_name_boxes, resize = True, config = '--psm 12')
            directors_address_string = ocr_boxes(img, directors_address_boxes, blur =True, resize = True, lang = 'chi_sim+eng', config = '--psm 12')
            directors_email_string = ocr_box(img, directors_email_box[1])

            hkid_1 = ocr_segmented_box(img, hkid_boxes[0][1], single = True, data_type = 'letter')
            hkid_2 = clean_hkid(ocr_segmented_box(img, hkid_boxes[1][1], single = True, data_type = 'number'))

            self.directors_name = clean_alphabet(directors_name_string)
            self.directors_address = check_empty(clean_chinese(directors_address_string))
            self.directors_email = directors_email_string if directors_email_string != '(Nil)' else 'None'

            if hkid_2 != 'None' and len(hkid_2) > 5:
                self.directors_hkid = hkid_1.replace(' ', '') + ' ' + hkid_2
            else:
                self.directors_hkid = 'None'

        @property
        def page_data(self):
            """
            Get data on Page 4.

            This function is available as a property.

            Returns
            -------
            dict
                Dictionary containing information on page 4
            """

            data = {
                'page_4':
                {
                'directors_name': self.directors_name,
                'directors_address': self.directors_address,
                'directors_email': self.directors_email,
                'directors_hkid': self.directors_hkid
                }
            }

            return data
    
    class PageEight(object):
        """
        Class representing the eigth page of the document

        Parameters
        ----------
        page_path : str
            Relative path to the eigth page of the document in JPEG fomat

        Attributes
        ----------
        directory_name : str
            Name of the directory from which this page was extracted
        shareholders_names : str
            Names of the shareholders
        shareholders_addresses : str
            Addresses of the shareholders
        shareholders_stake : str
            Stake of each shareholder

        Methods
        -------
        get_data()
            Get all information on page 8
        """
      
        def __init__(self, page_path):
            img = cv2.imread(page_path)
            skew_angle, boxes_info = process_image(img, cv2.RETR_EXTERNAL, approx_method = cv2.CHAIN_APPROX_NONE, skel = False, canny = True, vertical_iterations=3)
            if skew_angle > 0.15 or skew_angle < -0.15:
                img = rotate_image(img, skew_angle)

            box_of_interest = sorted(boxes_info, key = lambda box: box[0], reverse = True)[0]

            table = img[box_of_interest[1][1]:box_of_interest[1][1] + box_of_interest[1][3],box_of_interest[1][0]:box_of_interest[1][0] + box_of_interest[1][2]]
            table_gray = cv2.cvtColor(table, cv2.COLOR_BGR2GRAY)

            x_list, y_list = get_line_coordinates(table_gray, 7, 5)

            y = y_list[-2]
            height, width = table_gray.shape

            shareholders_names_box = table[y:height, x_list[0]:x_list[1]]
            shareholders_addresses_box = table[y:height, x_list[1]:x_list[2]]
            shareholders_stake_box = table[y:height, x_list[2]:x_list[3]]

            self.shareholders_names = separate_text(image_to_string(shareholders_names_box, lang='chi_sim+eng', config = '--psm 12'), nSpaces = 2, type = 'alphabet')
            self.shareholders_addresses = separate_text(image_to_string(shareholders_addresses_box, lang='chi_sim+eng', config = '--psm 12'))
            self.shareholders_stake = separate_text(image_to_string(shareholders_stake_box, lang='eng', config = '--psm 12'), nSpaces = 1, type = 'numbers')

        @property
        def page_data(self):
            """
            Get data on Page 8.

            This function is available as a property.

            Returns
            -------
            dict
                Dictionary containing information on page 8
            """

            data = {
                'page_8':
                {
                'shareholders_names': self.shareholders_names,
                'shareholders_addresses': self.shareholders_addresses,
                'shareholders_stake': self.shareholders_stake,
                }
            }

            return data
