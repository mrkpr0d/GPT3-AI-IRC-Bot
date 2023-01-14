#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GPT3-IRC-Bot
Developed by mrkprod (Oscar Becerra)

This program is a chat bot for IRC that utilizes GPT-3 with the OpenAI API.

Copyright (C) 2021 mrkprod

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; see the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.

Contact information:
Email: osc.bec.lar@gmail.com

IMPORTANT: This program currently has some bugs, such as the !code parameter which allows
uploading code to dpaste.com and cannot add authenticated users by commands.
"""

import irc.bot
import requests
import json
import openai
import os
import time
import re
from jaraco.stream import buffer

# Lista de usuarios que pueden realizar peticiones
ALLOWED_USERS = ["mrkprod", "nick2"]
ADMIN_USER = ["mrkprod"] # ONLY USED BY !raw command for join channels, say msg, etc
SERVER = "irc.irc-hispano.org"
CHANNELS = "#inteligencia_artificial"
BOTNICK = "GPT3_Bot_"

# All users can chat with bot using next syntax on irc channel: 
# Botnick: Prompt 
ALLOW_ALL_USERS = True

# API KEYS Open AI
OPENAI_API_KEY = "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"
# API DPASTE TO SHARE CODE WITH !code command
DPASTE_API_KEY = "314d89b1d25a6156"

# ================================================================================================
#
#   Detector de lenguaje de programación para el comando !code
#
# ================================================================================================

def detect_syntax(text):
    language_patterns = {
        'Python': 'python',
        'Java': 'java',
        'C++': 'c++',
        'JavaScript': 'javascript',
        'HTML': 'html',
        'PHP': 'php',
        'CSS': 'css'
    }
    for language, pattern in language_patterns.items():
        if re.search(pattern, text.capitalize(), re.IGNORECASE):
            return pattern
    return 'Desconocido'

# ================================================================================================
#
#   CLASE GPT3BOT
#
# ================================================================================================

class GPT3Bot(irc.bot.SingleServerIRCBot):
    def __init__(self, server, channel, nick):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, 6667)], nick, nick)
    
        self.connection.buffer_class = buffer.LenientDecodingLineBuffer # fix para el error de buffer con símbolos raros
        self.channel = channel
        
    
    def on_welcome(self, c, e):
        channels = self.channel.split(",")
        for channel in channels:
            c.join(channel)
        
    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        
        a = e.arguments[0].split(":", 1)
        print('C>>')
        print(c)
        print('A>>')
        print(a)
        print("-----------------------------------------")
        print(e)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return
       


    def do_command(self, e, cmd):
        
        nick = e.source.nick
        c = self.connection
        print('FULL CMD >> '+cmd)
        print('PROMPT >> '+cmd)

        question = cmd
        
        if nick not in ALLOWED_USERS or not ALLOW_ALL_USERS: # Chequeamos que el usuario está en la lista de admins
            return
       
        if cmd == "disconnect":  # Desconectamos del servidor
            self.disconnect()
            return
        if cmd[:4] == "!raw" and nick == ADMIN_USER: # ADMIN NICK FOR IRC RAW COMMANDS
            param = cmd[5:]
            print(param)
            self.connection.send_raw(format(param))
            return

        # ================================================================================================
        #
        #   CODE MODULE: Conecta con Open AI y sube el codigo generado a DPASTE
        #
        # ================================================================================================

        if cmd[:5] == "!code": # Cargamos el modulo para codigo
            print('Question Code>>'+question[4:])

            # Detectamos el lenguaje solicitado para indicarlo en dpaste
            syntax=detect_syntax(question)
            while True:
                try:
                    start_sequence = "\nAI:"
                    restart_sequence = "\nHuman: "

                    openai.api_key = OPENAI_API_KEY
                    r = openai.Completion.create(
                        model="text-davinci-002",
                        prompt=question,
                        temperature=0.9,
                        max_tokens=1000,
                        top_p=1,
                        frequency_penalty=0,
                        presence_penalty=0,
                    )
                    #print(r)
                    break
                except openai.error.RateLimitError:
                    #esperar antes de volver a intentar
                    time.sleep(5)

            if r.created:
                if e.target:
                    text = r.choices[0].text.replace("\n", "\r")
                    # --------- DEBUG ---------
                    print(e.target)
                    print('==============================')
                    print(r)


                    url = "https://dpaste.com/api/"
                    headerspaste = {
                        "User-Agent": "GPT3Bot",
                        "Authorization": "Bearer "+DPASTE_API_KEY
                    }
                    datapaste = {
                        "content": text,
                        "syntax": syntax,
                        "expires": "1d",
                    }

                    rpaste = requests.post(url, data=datapaste, headers=headerspaste)
                    print(rpaste)

                    if rpaste.status_code == 201:
                        result = "Aqui tienes " + e.source.nick + " -> " + rpaste.text.replace("\n","\r") + " ("+syntax+")"
                        print(result)
                        if r.created:
                            if e.target:

                                c.privmsg(e.target, result)
                                print(e.target)
                                print('==============================')
                                #print(r)
                    else:
                        error = "Error al subir el contenido a dpaste"
                        print(error)
                        c.privmsg(e.target, error)

        # ================================================================================================
        #
        #   CHAT MODULE: Conecta con Open AI y envia el texto al canal donde le hicieron la peticion.
        #
        # ================================================================================================

        elif cmd: 
            print('Question >> '+question)
                
            while True:
                try:
                    start_sequence = "\nHuman: "
                    restart_sequence = "\n"

                    openai.api_key = OPENAI_API_KEY
                    r = openai.Completion.create(
                        model="text-davinci-003",
                        prompt="Human: "+question,
                        temperature=0.9,
                        max_tokens=500,
                        top_p=1,
                        frequency_penalty=0,
                        presence_penalty=0,
                        stop=[" Human:", " Robot:"]
                    )
                    #print(r)
                    break
                except openai.error.RateLimitError:
                    #esperar antes de volver a intentar
                    time.sleep(5)
            if r.created:
                if e.target:
                    text =  r.choices[0].text.replace("\n", " ").split(":", 1)
                    size_limit=400
                    if len(text) > 1:
                        
                        splittext1 = re.sub(r'\\u00[\da-fA-F]{2}', '', text[1].strip()) # # QUITAMOS UNICODES Y PRIMER ESPACIO EN BLANCO
                        text_blocks = [splittext1[i:i+size_limit] for i in range(0, len(splittext1), size_limit)]
                        print(text_blocks)
                        for block in text_blocks:
                            # Enviamos texto al chat filtrando los Robot: AI:
                            c.privmsg(e.target, block )
                            print(block)
                            
                    else:
                        text = r.choices[0].text.replace("\n", " ")
                        splittext0 = re.sub(r'\\u00[\da-fA-F]{2}', '', text.strip()) # QUITAMOS UNICODES Y PRIMER ESPACIO EN BLANCO
                        text_blocks = [splittext0[i:i+size_limit] for i in range(0, len(splittext0), size_limit)]
                        for block in text_blocks:
                            # Enviamos texto al chat filtrando los Robot: AI:
                            c.privmsg(e.target, block )
                            print(block)
                        #splittext0 = re.sub(r'\\u00[\da-fA-F]{2}', '', text[0].strip()) # QUITAMOS UNICODES Y PRIMER ESPACIO EN BLANCO
                        #text_blocks = [splittext0[i:i+450] for i in range(0, len(splittext0), 450)]
                        #c.privmsg(e.target, text_blocks )
                    
                        # --------- DEBUG ---------
                        print(e.target)
                        print('==============================')
                        print(r)
        # else:
            #    c.privmsg(e.source, "Error al comunicar con OpenAI API.")


bot = GPT3Bot(SERVER, CHANNELS, BOTNICK)
bot.start()
