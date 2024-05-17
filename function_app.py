import base64
from datetime import datetime
import azure.functions as func
import logging
import json
import io
from fitz import pymupdf
from PIL import Image
from pypdf import PdfReader

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="http_extract_images_data_fitz")
def http_extract_images_data_fitz(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Begin funciton http_extract_images_data_fitz")
    
    try:
        # Read the PDF file from the HTTP request
        logging.info("Getting file from body of request.")
        pdf_file = req.get_body()
        if pdf_file is None:
            return func.HttpResponse(json.dumps([]),status_code=200)
        try:
            logging.info(f'Decoding from base64 to bytes.')
            byte_file = base64.b64decode(pdf_file)
        except Exception as e:
            return func.HttpResponse(f'An error occured when decoding the file. [Error: {repr(e)}]',status_code=500)
       
        try:
            logging.info(f'Converting to IO bytes')
            io_byte_file = io.BytesIO(byte_file)
        except Exception as e:
            return func.HttpResponse(f'An error occured when conveting the file to IO bytes. [Error: {repr(e)}]',status_code=500)
        
        
        # Process the PDF and extract images
        logging.info("begin processing the file")
        return_list = {"images":[],"metadata":{}}
        try:
            images_list = get_image_list(io_byte_file)
        except Exception as e:
            return func.HttpResponse(body=f'Error get_image_list: {repr(e)}', mimetype="application/json", status_code=500)
        try:
            image_list_binary = set_image_binary(pdf_stream=io_byte_file,images_list=images_list)
            if image_list_binary is not None:
                return_list['images'] = image_list_binary
        except Exception as e:
            return func.HttpResponse(body=f'Error set_image_binary: {repr(e)}', mimetype="application/json", status_code=500)
        try:
            document_metadata = get_document_metadata(pdf_stream=io_byte_file)
            if document_metadata is not None:
                return_list["metadata"]= document_metadata
        except Exception as e:
            return func.HttpResponse(body=f'Error get_document_metadata: {repr(e)}', mimetype="application/json", status_code=500)
        # Return the images and their data as a JSON response
        return func.HttpResponse(body=json.dumps(return_list), mimetype="application/json", status_code=200)
    except Exception as e:
        return func.HttpResponse(f"An error occurred: {str(e)}", status_code=500)
    
def set_image_binary(pdf_stream,images_list):
    i_list = images_list
    if len(images_list) > 0 and pdf_stream is not None:
        reader = PdfReader(pdf_stream)
        image_list_index = 0
        num_pages = len(reader.pages)
        print(f'num_pages: {num_pages}')
        for j in range(len(reader.pages)):
            page = reader.pages[j]
            for i in page.images:
                logging.info(f'image found: {i.name}')
                current_image = None
                logging.info(f'Encoding current image to base64 then utf-8')
                imageObj = base64.b64encode(i.data).decode('utf-8')

            
            #current_image = {"seq_num":seq_num,i.name:imageObj}
                if 'img' in images_list[image_list_index]:
                    logging.info(f'setting image binary data')
                    i_list[image_list_index]['img'] = imageObj
                    image_list_index +=1
            #write image to file system
            #with open(i.name,'wb') as f:
                #f.write(i.data)
            logging.info(f'set_image_binary completed processing.')
    return i_list
def get_document_metadata(pdf_stream):
    pdf_file = pymupdf.Document(stream=pdf_stream, filetype="pdf")
    metadata = {"author":"","creationDate":""}
    author = ''
    creationDate = ''
    pdf_metadata = pdf_file.metadata
    if 'author' in pdf_metadata:
        author = pdf_metadata['author']
    if 'creationDate' in pdf_metadata:
        creationDate = pdf_metadata['creationDate'].split('D:')[1].split('-')[0]
        formattted_date = datetime.strptime(creationDate, '%Y%m%d%H%M%S').strftime('%m/%d/%Y %I:%M%p')
    metadata['author'] = author
    metadata['creationDate'] = formattted_date

    return metadata


def get_image_list(pdf_stream):
        pdf_file = pymupdf.Document(stream=pdf_stream, filetype="pdf")
        images_list = []

        
        page_nums = len(pdf_file)
        seq_num = 1
        for page_num in range(page_nums):
            page_content = pdf_file[page_num]
            current_images = page_content.get_images()
            for i in range(0,len(current_images)):
                #0=xref, 7=name, 2=width, 3=height
                images_list.append({"page":page_num+1,"img_index":i,"seq_num":seq_num,"name":current_images[i][7],"width":current_images[i][2],"height":current_images[i][3],"img":""})
                seq_num += 1
        return images_list


    logging.info("Open the file in a stream.")
    # Open the PDF file from the stream
    pdf = pymupdf.Document(stream=pdf_stream, filetype="pdf")
    pdf_metadata= pdf.metadata
    pdf_table_of_contents = pdf.get_toc()
    images_data = []
    logging.info("Begin iterating the pages.")
    # Iterate through each page
    for page_index in range(len(pdf)): # iterate over pdf pages
        page = pdf[page_index] # get the page
        image_list = page.get_images()

        # print the number of images found on the page
        if image_list:
            print(f"Found {len(image_list)} images on page {page_index}")
        else:
            print("No images found on page", page_index)

        for image_index, img in enumerate(image_list, start=1): # enumerate the image list
            current_image = {}
            xref = img[0] # get the XREF of the image
            pix = pymupdf.Pixmap(pdf, xref) # create a Pixmap

            if pix.n - pix.alpha > 3: # CMYK: convert to RGB first
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            current_image = {"name":"imb_name","offset":xref,"image_data":"data_here"}
            images_data.append(pix)
            #pix.save("page_%s-image_%s.png" % (page_index, image_index)) # save the image as png
            pix = None


    return images_data