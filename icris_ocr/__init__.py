"""
icris_ocr - a Python automation tool for extracting data from PDF documents
using computer vision techniques
===========================================================================

**icris_ocr** is a Python automation tool that makes extracting data from
PDF documents convenient. It provides packages for each part of the OCR
process--from PDF conversion and document classification to edge detection
and data cleaning. 

Currently, it provides utilities for annual return documents.

>>> from icris_ocr import AnnualReturn
>>> document_directory = 'path/to/document_directory_of_company_x'
>>> company_x = AnnualReturn(document_directory)
>>> data = company_x.doc_data.T # Transpose the returned dataframe

"""

import multiprocessing as mp
import traceback

from .document_layouts import *

def process_doc_dir(doc_dir, doc_type = 'Annual Return'):
    """
    Process all images of a document's pages
    
    Parameters
    ----------
    doc_dir : str
        Relative path to the directory containing images of document pages
    doc_type : str
        Specify type of document (default = 'Annual Return')

    Returns
    -------
    doc_data : pandas.DataFrame
        Dataframe containing all information in a document
    """

    if os.path.isdir(doc_dir):
        if doc_type == 'Annual Return':
            doc_instance = AnnualReturn(doc_dir)
            doc_data = doc_instance.doc_data
            return doc_data

def process_dir(dir, doc_type = 'Annual Return', parallel = False):
    """
    Process all document directories in a directory

    Parameters
    ----------
    dir : str
        Relative path to directory containing the document directories
    doc_type : str
        Type of documents (default = 'Annual Return')
    parallel : bool
        Process directories in parallel for faster performance

    Returns
    -------
    data_df : pandas.DataFrame
        Dataframe containing information about all document directories 
        processed successfully
    failed_df : pandas.DataFrame
        Dataframe containing information about all document directories 
        processed unsuccessfully and their corresponding traceback
    """

    doc_data_list = []
    failed_list = []

    if parallel:
        completed = 0
        def worker(input, output, failed):
            nonlocal completed
            for doc_dir in iter(input.get, 'STOP'):
                completed += 1
                try:
                    doc_data = process_doc_dir(doc_dir, doc_type)
                    assert (isinstance(doc_data, pd.DataFrame) or isinstance(doc_data, pd.Series))
                    output.put(doc_data)
                except:
                    exception = traceback.format_exc(7)
                    failed.put((doc_dir, exception))
                print(f'\t\t****{mp.current_process().name} is at iteration {completed}****')

        NUMBER_OF_PROCESSES = mp.cpu_count() 

        doc_list = [f'{dir}/{doc_dir}' for doc_dir in os.listdir(dir) if os.path.isdir(f'{dir}/{doc_dir}')]
        num_doc = len(doc_list)

        print(f"\t\t****Total documents to be processed: {num_doc}****\n\n")

        task_manager = mp.Manager()
        done_manager = mp.Manager()
        failed_manager = mp.Manager()

        task_queue = task_manager.Queue()
        done_queue = done_manager.Queue()
        failed_queue = failed_manager.Queue()
            
        for doc_dir in doc_list:
            task_queue.put(doc_dir)

        for i in range(NUMBER_OF_PROCESSES):
            task_queue.put('STOP')

        process_list = [mp.Process(name = f'Process {str(i)}', target=worker, args=(task_queue, done_queue, failed_queue)) for i in range(NUMBER_OF_PROCESSES)]

        for process in process_list:
            process.start()

        for process in process_list:
            process.join()

        while not done_queue.empty():
            doc_data_list.append(done_queue.get())
        
        while not failed_queue.empty():
            failed_list.append(failed_queue.get())

    else:
        doc_list = [f'{dir}/{doc_dir}' for doc_dir in os.listdir(dir) if os.path.isdir(f'{dir}/{doc_dir}')]
        num_doc = len(doc_list)

        print(f"\t\t****Total documents to be processed: {num_doc}****\n\n")

        for count, doc_dir in enumerate(doc_list):
            print(f'\t\t****{count} items processed out of {num_doc}****')
            try:
                doc_data = process_doc_dir(doc_dir, doc_type)
                doc_data_list.append(doc_data)
            except:
                exception = traceback.format_exc(7)
                failed_list.append((doc_dir, exception))
        
    if len(failed_list) != 0:
        failed_df = pd.Series(dict(failed_list))
    else:
        failed_df = pd.Series(['There were no exceptions'])

    if len(doc_data_list) != 0:
        data_df = pd.concat(doc_data_list, axis = 0, sort=False)
    else:
        data_df = pd.Series(['No documents were scraped successfully'])

    print('\t\t****Task completed****')

    return (data_df, failed_df)