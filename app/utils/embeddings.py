import streamlit as st
from typing import List, Dict, Any, Optional
import json
from PyPDF2 import PdfReader
from openai import OpenAI
import tiktoken
from concurrent.futures import ThreadPoolExecutor
import time
import os
import re

client = OpenAI()

METHODS = ['openai']
EMB_CALLS = 0
GPT_CALLS = 0
GPT_TOKENS = 0
EMB_TOKENS = 0
NUM_WORKERS = 10
AVOID_PREPROCESSING = True
DEBUG = os.environ.get('DEBUG', False)

def count_tokens(txt: str, encoding_name: str) -> int:
    """Number of tokens used by OpenAI tokenizer."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(txt))
    return num_tokens


def parse_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """
    Return a list of dictionaries containing text with metadata.
    Dictionary:
        name -> Document name
        page -> Page number
        content -> Page text
    """
    pages_text = []
    reader = PdfReader(pdf_path)
    for k, page in enumerate(reader.pages):
        new = {
            'name': pdf_path,
            'page': k + 1,
            'content': page.extract_text()
        }
        pages_text.append(new)
    return pages_text

def parse_pdf_without_references(pdf_path: str) -> List[Dict[str, str]]:
    """
    Return a list of dictionaries containing text with metadata.
    SIN REFERENCIAS. EN EL PATTERN INDICAR LA PALABRA DE INICIO DE LAS REFERENCIAS
    Dictionary:
        name -> Document name
        page -> Page number
        content -> Page text
    Extracts content without references.
    """
    pages_text = []
    reader = PdfReader(pdf_path)
    pattern = re.compile(r"(Referencias|Véase también)", re.IGNORECASE)
    references_found = False
    
    for k, page in enumerate(reader.pages):
        page_text = page.extract_text()   
        if not references_found:
            match = pattern.search(page_text)
            if match:
                page_text = page_text[:match.start()]
                references_found = True  
        new = {
            'name': pdf_path,
            'page': k + 1,
            'content': page_text
        }
        pages_text.append(new)     
        if references_found:
            break
    return pages_text

def preprocess_text(text: str) -> str:
    """Uses chatgpt to clean any text."""
    global GPT_CALLS, GPT_TOKENS, DEBUG
    GPT_CALLS += 1
    GPT_TOKENS += count_tokens(text, 'cl100k_base')
    messages = [
        {"role": "system", "content": 'You are a text cleaner. Your job is to make the text the user gives you as readable as possible. As part of your tasks you have to correct accents that were wrongly parsed, remove emails and phone numbers or eliminate innecessary punctuation marks. Ensure that the text is readable and only return the corrected text nothing else. Avoid all formalities and explanations, just return the clean text in the language provided and nothing else.'},
        {"role": "user", "content": text},
    ]
    if DEBUG or AVOID_PREPROCESSING:
        return text
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.2
    )
    return response.choices[0].message.content

def preprocess_page(pages_text: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    For each page it cleans the text, removing unnecesary punctuation or useless content.
    """
   
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as exec:
        futures = []
        for page in pages_text:
            futures.append(exec.submit(preprocess_text, page['content']))
   
        for page, future in zip(pages_text, futures):
            page['content'] = future.result()
            
    return pages_text

def extract_chunks(pages_text: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Separates the pages' text into chunks.
    The dictionary now contains and additional key: chunk, representing chunk number.
    """
    chunks = []
    for k, page in enumerate(pages_text):
       
        strings = split_strings(page['content'], max_tokens=2000)
        for k, string in enumerate(strings):
            new = {
                'name': page['name'],
                'page': page['page'],
                'chunk': k,
                'content': string
            }
            chunks.append(new)
    
    return chunks

def translate(text: str) -> str:
    """From any language to English (ChatGPT). Preferably from spanish."""
    global GPT_CALLS, GPT_TOKENS, DEBUG
    GPT_CALLS += 1
    GPT_TOKENS += count_tokens(text, 'cl100k_base')
    messages = [
        {"role": "system", "content": "You are an expert translator. Your only job is to translate whatever the user gives you into english. Respect any technical term or name  you don't recognise as it is. Respect numbers too. Avoid all formalities and explanations, just return the translated text and nothing else."},
        {"role": "user", "content": text},
    ]
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )
    return_res = response.choices[0].message.content
    return return_res

def preprocess_chunks(chunks: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Translated text.
    Future improvement: merge and re-split chunks that were incorrectly separated by a page break.
    """
    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as exec:
        futures = []
        for chunk in chunks:
            futures.append(exec.submit(translate, chunk['content']))
        for chunk, future in zip(chunks, futures):
            chunk['content-en'] = future.result()
    return chunks

def embed(text: str, method: str) -> List[float]:
    """
    Given a chunk of text, embed it using the given method.
    Text must no be void.
    """
    global EMB_CALLS, EMB_TOKENS, DEBUG
    EMB_CALLS += 1
    EMB_TOKENS += count_tokens(text, 'cl100k_base')
    if method == 'openai':
        text = text.replace("\n", " ")
        return client.embeddings.create(input=[text], model='text-embedding-ada-002').data[0].embedding


def vectorize(chunks: List[Dict[str, str]], method: str) -> List[Dict[str, Any]]:
    """
    For each chunk, embed the text into a vector.
    The content key remains the text, but a new vector key is added to dictionary.
    """
    vectors = []
    for chunk in enumerate(chunks):
    
        new = {}
        if chunk['content-en'] == '':
            continue
        new['name'] = chunk['name']
        new['page'] = chunk['page']
        new['chunk'] = chunk['chunk']
        new['content'] = chunk['content']
        new['vector'] = embed(chunk['content-en'], method)
        vectors.append(new)
    return vectors

def save(vectors: List[Dict[str, Any]], emb_path: str):
    """
    Saves vectors and metadata in json format.
    """
    with open(emb_path, 'w') as f:
        json.dump(vectors, f)

def process_file(pdf_path: str, method: str) -> List[Dict[str, Any]]:
    """
    Converts a pdf into a set of vectors representing the internal content.
    Each vector is saved together with its metadata into a json file.
    """
    pages_text = parse_pdf(pdf_path)
    pages_text = preprocess_page(pages_text)
    chunks = extract_chunks(pages_text)
    chunks = preprocess_chunks(chunks)
    vectors = vectorize(chunks, method)
    return vectors

def num_tokens(text: str) -> int:
    """Return the number of tokens in a string."""
    encoding = tiktoken.get_encoding('cl100k_base')
    return len(encoding.encode(text))

def halved_by_delimiter(string: str, delimiter: str = "\n") -> list[str, str]:
    """Split a string in two, on a delimiter, trying to balance tokens on each side."""
    chunks = string.split(delimiter)
    if len(chunks) == 1:
        return [string, ""]  # no delimiter found
    elif len(chunks) == 2:
        return chunks  # no need to search for halfway point
    else:
        total_tokens = num_tokens(string)
        halfway = total_tokens // 2
        best_diff = halfway
        for i in range(len(chunks)):
            left = delimiter.join(chunks[: i + 1])
            left_tokens = num_tokens(left)
            diff = abs(halfway - left_tokens)
            if diff >= best_diff:
                break
            else:
                best_diff = diff
        left = delimiter.join(chunks[:i])
        right = delimiter.join(chunks[i:])
        return [left, right]


def truncated_string(
    string: str,
    max_tokens: int,
    print_warning: bool = True,
) -> str:
    """Truncate a string to a maximum number of tokens."""
    encoding = tiktoken.get_encoding('cl100k_base')
    encoded_string = encoding.encode(string)
    truncated_string = encoding.decode(encoded_string[:max_tokens])
    if print_warning and len(encoded_string) > max_tokens:
        print(f"Warning: Truncated string from {len(encoded_string)} tokens to {max_tokens} tokens.")
    return truncated_string


def split_strings(
    string: str,
    max_tokens: int = 1000,
    max_recursion: int = 5,
) -> list[str]:
    """
    Split a subsection into a list of subsections, each with no more than max_tokens.
    Each subsection is a tuple of parent titles [H1, H2, ...] and text (str).
    """
    num_tokens_in_string = num_tokens(string)
    # if length is fine, return string
    if num_tokens_in_string <= max_tokens:
        return [string]
    # if recursion hasn't found a split after X iterations, just truncate
    elif max_recursion == 0:
        return [truncated_string(string, max_tokens=max_tokens)]
    # otherwise, split in half and recurse
    else:
        for delimiter in ["\n\n", "\n", ". "]:
            left, right = halved_by_delimiter(string, delimiter=delimiter)
            if left == "" or right == "":
                # if either half is empty, retry with a more fine-grained delimiter
                continue
            else:
                # recurse on each half
                results = []
                for half in [left, right]:
                    half_strings = split_strings(
                        half,
                        max_tokens=max_tokens,
                        max_recursion=max_recursion - 1,
                    )
                    results.extend(half_strings)
                return results
    # otherwise no split was found, so just truncate (should be very rare)
    return [truncated_string(string, max_tokens=max_tokens)]
