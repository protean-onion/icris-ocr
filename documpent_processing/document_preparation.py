"""
This module defines functions that prepare PDF documents for OCR.

"""

import re
import os
import multiprocessing as mp
import threading
import multiprocessing as mp
from queue import Queue

import pytesseract
import pdf2image as pdf

def remove_duplicates(paths):
    """
    Remove document duplicates based on directory names with spaced digits.

    Parameters
    ----------
    names : list
        List containing relative paths to directories or files
    
    """

    def check_digit(string_list):
        """
        Check if string has digits at the end.

        Parameters
        ----------
        string_list : list
            List of parts of a string delimited by spaces

        Returns
        -------
        isdigit : bool
            Boolean specifying whether the string is a duplicate
        
        """

        if len(string_list) == 1:
            isdigit = False
        
        else:
            check_string = string_list[-1]
            check_string = re.sub(r'[^0-9]', '', check_string)
            isdigit = check_string.isdigit()
        return isdigit
    
    directory_path = '/'.join(paths[0].split('/')[:-1])
    extension = None
    if '.' in paths[0]:
        extension = os.path.splitext(paths[0])[1]

    paths = [os.path.splitext(path)[0] for path in paths]
    names = [path.split('/')[-1] for path in paths]

    # Remove all closing digits from the name
    processed_names = [re.sub(r'\s{1,}', ' ', name).strip() for name in names]
    split_names = [name.split(' ') for name in processed_names]
    duplicates_removed = [directory_path + '/' + ' '.join(name) for name in split_names if not check_digit(name)]
    
    if not extension is None:
        duplicates_removed = [name + extension for name in duplicates_removed]

    return duplicates_removed

def convert(pdf_file):
    """
    Convert each page of a PDF file to a JPEG file and store in a
    directory, which is given the base name of the file.

    Parameters
    ----------
    pdf_file : str
        Path to PDF file in current directory
    
    """

    if os.path.splitext(pdf_file)[1] == '.pdf':
        file_name = str(pdf_file)[:-4]
        try:
            file = pdf.convert_from_path(pdf_file, 330)
            try:
                os.mkdir(file_name)
            except:
                pass
            for count, page in enumerate(file,1):
                page_name = "page_"+ str(count)+ ".jpg"
                page.save(str(os.getcwd()) + '/' + file_name + '/' + page_name, 'JPEG')
        except:
            print(f'{pdf_file} could not be converted')
    else:
        print(f'{pdf_file} is not a PDF')

def dir_convert(directory, parallel=True):
    """
    Convert a directory of PDF files.
    
    Parameters
    ----------
    directory : str
        Path to directory containing PDF files

    """

    def convert_pdf(pdf_file):
        """
        Convert PDF file to JPEG images.

        Parameters
        ----------
        pdf_file : str
            Relative path to PDF file
        target_directory : str
            Directory in the current directory to store images in
        
        """

        file_parts = os.path.splitext(pdf_file)

        if file_parts[1] == '.pdf':
            jpeg_file = pdf.convert_from_path(f'{directory}/{pdf_file}', 330)
            document_directory = current_dir + '/' + target_directory + '/' + file_parts[0]

            try:
                os.mkdir(document_directory)
            except Exception:
                pass

            for order, page in enumerate(jpeg_file,1):
                page_name = document_directory + "/page_" + str(order) + ".jpg"
                page.save(page_name, 'JPEG')

    current_dir = os.getcwd()

    unsuccessful_list = []

    completed = 0

    if os.path.isdir(directory):
    
        target_directory = directory + '_JPEGs'
        try:
            os.mkdir(target_directory)
        except Exception:
            pass

        files = os.listdir(directory)
        files = remove_duplicates(files)
        number_of_files = len(files)

        if parallel:

            def worker(input_queue, unsuccessful_queue):
                nonlocal current_dir, completed

                for pdf_file in iter(input_queue.get, 'STOP'):
                    print(f'{mp.current_process().name} is at iteration {completed}')
                    completed += 1
                    try:
                        convert_pdf(pdf_file)
                    except:
                        unsuccessful += 1
                        unsuccessful_queue.put(pdf_file)
            
            NUMBER_OF_PROCESSES = mp.cpu_count() // 2

            print(f"\t\t****Total documents to be processed: {number_of_files}****\n\n")

            task_manager = mp.Manager()
            unsuccessful_manager = mp.Manager()

            task_queue = task_manager.Queue()
            unsuccessful_queue = unsuccessful_manager.Queue()

            for pdf_file in files:
                task_queue.put(pdf_file)

            for i in range(NUMBER_OF_PROCESSES):
                task_queue.put('STOP')

            process_list = [mp.Process(
                name=f'Process {str(i)}',
                target=worker, args=(task_queue,
                unsuccessful_queue))
                for i in range(NUMBER_OF_PROCESSES)]

            for process in process_list:
                process.start()

            for process in process_list:
                process.join()

            while not task_queue.empty():
                pass

            while not unsuccessful_queue.empty():
                unsuccessful_list.append(unsuccessful_queue.get())
            
        else:
            print(f'{len(files)} files to be converted')
            
            for order, pdf_file in enumerate(files):
                try:
                    convert_pdf(pdf_file)
                except:
                    unsuccessful_list.append(pdf_file)
                print(f'{order} files processed')
            

    if len(unsuccessful_list) > 0:
        print('The following files could not be converted:')
        for order, pdf_file in enumerate(unsuccessful_list, 1):
            print(f'{str(order)}. {pdf_file}')
    else:
        print('All files converted successfully')

def categorize(
    directory,
    doc_types=[
        'Annual Return',
        'Incorporation Form',
        'Notice of Change of Director',
        'Notice of Change of Company Secretary',
        'Notice of Alteration of Share Capital',
        'Notice of Change in Particulars of Company Secretary',
        'Notice of Change of Address',
        'Notice of Resignation',
        'Return of Allotment',
        ]
        ):
    """
    Categorize directory of document page images based on a the title 
    of the first page in the directory.

    Parameters
    ----------
    directory : str
        Path to document directory
    doc_types : list, optional
        List of strings specifying types of document to categorize, 
        default ['Annual Return', 'Incorporation Form', 
        'Notice of Change of Director', 'Notice of Chage of Company Secretary']

    """

    assert os.path.isdir(directory), "Argument `directory` must be a string specifying relative path to document directory"

    if os.path.isdir(directory):
        current_directory = os.getcwd()

        # Individual components of the path to document directory
        path_components = directory.split('/')
        number_of_components = len(path_components)

        if number_of_components > 1:
            os.chdir('/'.join(path_components[:-1]))
            directory = path_components[-1]

        try:
            doc_string = re.sub(r'\n{1,}', ' ', str(pytesseract.image_to_string(
                f'{directory}/page_1.jpg')).strip())
            
            match = False
            for doc_type in doc_types:
                doc_pattern = re.compile(r'%s' % format(doc_type))
                matches = doc_pattern.findall(doc_string)

                if len(matches) > 0:
                    
                    try:
                        os.mkdir(doc_type)
                    except:
                        pass

                    if 'Non-Hong Kong' in doc_string:
                        try:
                            os.mkdir(f'{doc_type}/{doc_type}s of Registered Non-Hong Kong Companies/{directory}')
                        except:
                            pass
                        os.rename(directory, f'{doc_type}/{doc_type}s of Registered Non-Hong Kong Companies/{directory}')
                    elif 'Ordinance' in doc_string:
                        try:
                            os.mkdir(f'{doc_type}/{doc_type}s of Registered Non-Hong Kong Companies/{directory}')
                        except:
                            pass
                        os.rename(directory, f'{doc_type}/{doc_type}s of Registered Non-Hong Kong Companies/{directory}')
                    else:
                        try:
                            os.mkdir(f'{doc_type}/{doc_type}')
                        except:
                            pass
                        os.rename(directory,f'{doc_type}/{doc_type}/{directory}') 
                    
                    print(f'Document {directory} is of type `{doc_type}`')
                    match = True
                    break
            
            if not match:
                try:
                    os.mkdir('Miscellaneous')
                except:
                    pass
                os.rename(directory, f'Miscellaneous/{directory}')

        except:
            print(f'Directory {directory} could not be categorized')

        finally:
            os.chdir(current_directory)

def dir_categorize(
                directory,
                doc_types=[
                    'Annual Return',
                    'Incorporation Form',
                    'Notice of Change of Director',
                    'Notice of Change of Company Secretary',],
                parallel=True):
    """
    Categorize all document directories in a directory.

    Parameters
    ----------
    directory : str
        Directory name that is in the current directory
    doc_types : list, optional
        List of strings specifying types of document to categorize, 
        default ['Annual Return', 'Incorporation Form', 
        'Notice of Change of Director', 'Notice of Chage of Company Secretary']
    parallel : bool
        Process in parallel, default `True`

    """

    document_directories = [directory + '/' + document_directory for document_directory in os.listdir(directory)]
    document_directories = remove_duplicates(document_directories)
    number_of_documents = len(document_directories)
    
    completed = 0

    if parallel:
        
        def worker(input_queue):
            nonlocal completed
            for document_directory in iter(input_queue.get, 'STOP'):
                # print(document_directory)
                completed += 1
                categorize(document_directory)
        
        print(f"\t\t****Total documents to be processed: {number_of_documents}****\n\n")

        NUMBER_OF_THREADS = mp.cpu_count()
        # task_manager = mp.Manager()
        task_queue = Queue()

        for document_directory in document_directories:
            task_queue.put(document_directory)

        for i in range(NUMBER_OF_THREADS):
            task_queue.put('STOP')

        process_list = [threading.Thread(
            name=f'Thread {str(i)}',
            target=worker,
            args=(task_queue,), daemon = True)
            for i in range(NUMBER_OF_THREADS)]

        for process in process_list:
            process.start()

        for process in process_list:
            process.join()
        
    else:
        print(f"\t\t****Total documents to be processed: {number_of_documents}****\n\n")

        for order, document_directory in enumerate(document_directories):
            if os.path.isdir(document_directory):
                categorize(document_directory, doc_types=doc_types)

            print(f'{order} documents processed')

    print('Categorization complete')

def convert_and_categorize(directory, parallel = True):
    """
    Convert PDF documents to JPEG format and categorize documents
    based on type.

    Parameters
    ----------
    directory : str
        Relative path to directory
    parallel : bool
        Process in parallel
    
    """
    
    target_directory = directory + 'JPEGs'

    dir_convert(directory, parallel=parallel)
    dir_categorize(target_directory, parallel=parallel)
