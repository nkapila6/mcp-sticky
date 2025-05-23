#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on 2025-05-18 10:00:00 Sunday

@author: Nikhil Kapila
"""

import webbrowser
from fastmcp import FastMCP, Context
# import os

from utils.fetch import fetch_image_url, fetch_tele_link # unused: , fetch_resource
from utils.fetch import make_meme_custom, make_meme_from_template
from utils.url_checker import is_url
from utils.save import save_image

mcp = FastMCP('MCP Sticky: Meme and Sticker Maker for WhatsApp and Telegram', 
              dependencies=['beautifulsoup4', 'json', 'requests'])

# preset paths
# RESOURCE_PATH = os.path.join(os.getcwd(), 'resources')
# KEYS_PATH = os.path.join(RESOURCE_PATH,'db_keys.pkl')
# DB_PATH = os.path.join(RESOURCE_PATH,'db.pkl')

# async def make_meme(message:str, ctx:Context):
@mcp.tool(
    tags={"first_step", "initialization"},
    annotations={"title": "Step 1: Fetch Templates", "chainPosition": "start"}
)
async def fetch_key_context(message:str, ctx:Context, limit:int=5)->dict:
    """
    THIS TOOL IS TO BE CALLED FIRST AND IS TO PROVIDE ADDITIONAL CONTEXT to the next tool `parse_message()`.
    DO NOT CALL THIS TOOL FIRST IF USER ASKS TO IGNORE PREDEFINED TEMPLATES OR ASKS YOU TO SEARCH. JUMP DIRECTLY TO PARSE_MESSAGE.
    Gives the LLM additional context on available predefined templates.
    
    Args:
        message (str): Input query to make a meme on.
        limit (int, default=5): Limit number of queries to not run out of LLM forward pass token limits.
        ctx (Context): Incoming context.

    Returns:
        dict: dictionary of message and available templates.
    """
    await ctx.info('Fetching keys for additional context.')

    from resources.db import templates
    import random

    # keys = random.sample(list(templates.keys()), limit)
    # samples = {k: templates[k] for k in keys}
    
    return dict(message=message, templates=templates)

@mcp.tool(
    tags={"second_step", "processing"},
    annotations={"title": "Step 2: Parse Message", "chainPosition": "middle", "requiresPrevious": "fetch_key_context"}
)
async def parse_message(d:dict, ctx:Context):
    """
    THIS TOOL IS TO BE CALLED SECOND AND IS TO PROVIDE ADDITIONAL CONTEXT to the next tool `generate_meme()`.
    The LLM receives an input of user message and existing meme template keys.
    The LLM is supposed to and analyze the incoming message and template to make a decision.

    1. Look at pre-defined templates in the incoming dictionary object.
        NOTE:
            - The templates are a dict where each key has following sub-keys: ['_self','blank','example','id','keywords','lines','name','overlays','source','styles'].
            - If the chosen template has multiple line as indicated by the `lines` value, return the <meme text> as a Python list of length "lines" where each line is a part of the template.
            - Create the link based on the text and the example in the db.
            - PREFER USING EXISTING TEMPLATES INSTEAD OF PERFORMING A SEARCH.
               If the templates do not fit the usecase, feel free to search.
            - If the user explicitly specifies you to search then perform a search.
            - When searching, keep in mind the `CONTENT GUARDRAILS` section.
        
    2. Based on your decision of using predefined templates or searching, format the output as follows:
        Format your message as a Python diction as per below.
            {
                'SEARCH': <search query or Python None value>,
                'LINK': <created link or Python None value>, using example in the template db.
                'TEXT': [<meme text>] (this is a Python list of len 1,2,3,4,5,6,8) based on `lines` value in template.
                'TEMPLATE_KEY': <"key" or Python None value>
            }

        IMPORTANT: Use Python's `None` for null values, NOT JSON's `null`.
        
        (i) If using pre-defined templates:
                A) `TEMPLATE_KEY` = chosen <"key"> from templates.
                B) If no link is created, `LINK` = None
                
        (ii) If the LLM decides or user asks to search:
                A) `TEMPLATE_KEY` = None
                B) `SEARCH` = search query.
                C) `LINK` = None as this will be generated later.
                
    The output of this tool goes to the next tool `generate_meme()`.

    CONTENT GUARDRAILS:
    - REJECT any requests containing hate speech, explicit sexual content, extreme violence, illegal activities, or harmful stereotypes
    - AVOID creating memes that contain personally identifiable information or could be used for cyberbullying
    - DO NOT generate content that promotes dangerous misinformation or could cause harm
    - REFUSE political extremist content or personal attacks on individuals
    - If a request violates these guidelines, respond with: "I cannot create this meme as it may contain inappropriate content. Please try a different request."

    Args:
        d (dict): receives input dictionary of message and meme template keys.
        ctx (Context): Incoming context.

    Returns:
        Nothing, the output of this tool function call should be sent to generate_meme().
        If it is EMPTY, send the message dict with a 'SEARCH' query to `generate_meme`.
    """
    await ctx.info('Parsing input message...')
    # print(d)
    
@mcp.tool(
    tags={"final_step", "generation"},
    annotations={"title": "Step 3: Generate Meme", "chainPosition": "end", "requiresPrevious": "parse_message"}
)
async def generate_meme(d:dict,
                        ctx:Context,
                        use_template:bool,
                        want_tele_sticker:bool=False,
                        save_as_image:bool=True)->str:
    """Generate memes. 
    Takes the input from the previous `parse_message` tool and allows the user to gnerate memes.

    Args:
        d (dict): Input dictionary.
        ctx (Context): Incoming context.
        use_template(bool, True or False): The LLM decides what to use based on decision in `parse_message`. Should be True or False.
        want_tele_sticker (bool, default=False): If the user wants a Telegram sticker.
        save_as_image (bool, default=True): Saves the image to the users desktop.

    Returns:
       meme_link (str, default): the generated meme link.
       if want_tele_sticker=True:
            tele_link (if want_tele_sticker=True): returns Telegram sticker.
       
    """
    await ctx.info('Stripping out search terms and meme text.')
    search_query, meme_text, dbkey = d['SEARCH'], d['TEXT'], d['TEMPLATE_KEY']

    print(d)
    if use_template is not True: 
        if isinstance(meme_text, list): meme_text = ' '.join(meme_text) # just in case
        url = fetch_image_url(search_query)
        meme_link = make_meme_custom(url, meme_text)
    else: 
        # some models cannot generate urls, in this case we check the key and create the link ourselves
        if is_url(d['LINK']):
            meme_link = d['LINK']
        else:
            from resources.db import templates
            url = templates[dbkey]['blank']
            meme_link = make_meme_from_template(url, meme_text)

    if save_as_image: 
        path = save_image(meme_link)
        webbrowser.open(meme_link, new=1, autoraise=True)
        print(f'Image saved at {path}.')

    if want_tele_sticker:
        tg_link = fetch_tele_link(meme_link)
        webbrowser.open(tg_link, new=1, autoraise=True)
        return tg_link

    return meme_link

# @mcp.resource(uri="resource://templates",
#               name="MemeTemplates",
#               description="DB with name and keys of predefined templates on memegen",
#               mime_type="application/json")
# async def fetch_template()->dict:
#     """Fetches dict db with predefined meme templates.

#     Returns:
#         dict object: dict db of meme templates.
#     """
#     return fetch_resource(KEYS_PATH)

# CLAUDE DESKTOP does not support MCP Sampling so approaching the problem differently.
# https://modelcontextprotocol.io/docs/concepts/sampling
# Using nested tool calling in the meantime 
#   (this is playing with fire at the moment (this whole MCP USB-C shit is fire anyway) until I find a better solution).
# async def parse_message(message:str, ctx:Context)->tuple:
#     await ctx.debug('Parsing input query by user.')

#     prompt=f"""
#     Analyze the message requesting a meme: "{message}"
#     Reply with the following:
#     1. What should I search for on Google Search to find an appropriate image? Give a clear search query.
#     2. What text should be placed on the meme? 

#     Format your response as:
#     SEARCH: [search query]
#     TEXT: [meme text]
#     """
#     response = await ctx.sample(messages=prompt)
#     await ctx.debug(f'Context sample returns response: {response}')

#     lines = response.text.strip().split('\n')
#     await ctx.debug(f'The lines stripped are {lines}.')

#     for line in lines:
#         if line.startswith('SEARCH'):
#             search_query = line.replace('SEARCH: ', '').strip()
#         elif line.startswith('TEXT'):
#             meme_text = line.replace('TEXT: ', '').strip()

#     return response


if __name__ == "__main__":
    mcp.run()
