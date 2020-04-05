# icris-ocr

**icris-ocr** is a Python automation tool for extracting information from documents purchased from the Hong Kong government's Integrated Companies Registry Information System. It provides high-level abstractions in the form of classes to make extraction of data from multiple documents convenient.

It provides utilities for each part of the OCR process--from PDF conversion and document classification to edge detection and data cleaning. Classes representing documents have been defined in the `document_layouts` module. The subpackage `document_processing` is composed of modules aimed at preparing documents, processing them, and cleaning the data extracted; these utilities are provided by the `doc_utils`, `ocr_tools`, and `string_processing` modules respectively.

Currently, it provides utilities for annual return documents. Support for other documents can be added with the optimized functions defined in `document_layouts.ocr_tools`.

## Installation

The package relies on Google's Tesseract engine and its Chinese character recognition data set. See installation instructions for the Tesseract engine [here](https://www.pyimagesearch.com/2017/07/03/installing-tesseract-for-ocr/). After installation of the Tesseract engine on your machine, download the Chinese character recognition data set [here](https://github.com/tesseract-ocr/tessdata) and add it to your `tessdata` directory, which can be found in the directory for the base Tesseract engine.

The package itself, along with its dependencies, can be installed by following the instructions listed [here](https://cets.seas.upenn.edu/answers/install-python-module.html).

## Usage

Documents can be converted and categorized with the `convert_and_categorize` function in the `document_processing.document_preparation` module. The following commands convert unique PDF files in the target directory to a directory of images of each page of a file grouped in a single directory. Then, it categorizes those directories based on the title of the document on the first page. This results in another directory being created at the level of the target directory and contains categorical directories for different document types.

```Python
>>> from icris_ocr.document_processing import document_preparation
>>> document_directory = 'path/to/directory'
>>> document_preparation.convert_and_categorize(document_directory)
```

Once categorized, data can be collectively extracted from categorical directories using the `process_dir` function. The function returns a Pandas `DataFrame` object containing information about every document contained in the categorical directory and can be used for further analysis.

```Python
>>> from icris_ocr import *
>>> directory = 'path/to/directory'
>>> df = process_dir(directory, doc_type='Annual Return', parallel=True)
>>> df.to_excel('OCR Results.xlsx') # Write to Excel file
```

The same result can be achieved from the command line.

```Bash
$ python -m icris_ocr path/to/directory -t Annual\ Return -p
```

## Notes

Despite the autor's optimization efforts, the computational nature of the project makes the process very time consuming. The project can be implemented in a lower language such as C in the future for improved performance.

## References

This project makes liberal usage of the algorithms shared by Doctor Adrian Rosebrock on his [website](https://www.pyimagesearch.com).

## License

This project has been distributed under the [MIT](https://github.com/adityaverma415/icris_ocr/blob/master/LICENSE) license.
