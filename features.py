#!/usr/bin/python3
# coding=utf-8

from datetime import date, datetime
from random import random
from time import sleep

import tinder_api as api
import json
import random
import sys

def get_matches_and_messages():
    tinder_matches = {} # { person_id : match_id }
    tinder_messages = {} # { message_id : { 'from': person_id, 'to': person_id, 'message': message } }
    updates = api.get_updates()
    for match in updates["matches"]:
        match_id = match["id"]
        person_id = match["participants"][0]
        tinder_matches[person_id] = match_id
        messages = match["messages"]
        for message in messages:
            message_id = message["_id"]
            info = {'from': message["from"], 'to': message["to"], 'message': message["message"]}

            tinder_messages[message_id] = info
    return (tinder_matches, tinder_messages)

def start_conversations():
    tinder_matches, tinder_messages = get_matches_and_messages()
    paired_users = get_paired_users() # { person_idA : person_idB }

    users_with_messages = list({tinder_messages[id]["from"] for id in tinder_messages}) + list({tinder_messages[id]["to"] for id in tinder_messages}) #TODO from | to
    no_chat_users = [id for id in tinder_matches if id not in users_with_messages]

    #we only want to send a message to one of the two pairs
    users_to_start = []
    for id in no_chat_users:
        pair = paired_users[id]
        if pair not in users_to_start:
            users_to_start.append(id)

    dumps(paired_users, "Paired users")
    dumps(no_chat_users, "No chat users")
    dumps(users_to_start, "Users to start")

    greetings = ["Hey!", "Hello!! :)", "Yo!", "Sup?", "G'day!", "Hiya!", "Hey hey"]

    for id in users_to_start:
        greeting = random.choice(greetings)
        send_to = tinder_matches[id]
        print("Send {} to {}".format(greeting, send_to), file=open("/home/aaron/Desktop/Tinder/messagelog.txt", "a"))
        result = api.send_msg(send_to, greeting)
        if "error" in result:
            print("Could not send message to {} @ {}".format(id, send_to))

def swipe_right(n):
    recs = api.get_recs_v2()["data"]["results"]

    bound = min(len(recs), n)
    for i in range(bound):
        rec = recs[i]
        result = api.like(rec["user"]["_id"])
        dumps(result, "Swipe right...")
        if i < bound-1:
            pause(.5, 3)

def pair_users():
    #get all the tinder data
    tinder_matches, tinder_messages = get_matches_and_messages()

    #read the existing pairs from our file and figure out what is new
    paired_users = get_paired_users() # { person_idA : person_idB }
    unpaired_users = [id for id in tinder_matches if id not in paired_users]
    ghosted_users = [id for id in paired_users if id not in tinder_matches]

    #unpair no_chat ghosted users
    users_with_messages = list({tinder_messages[id]["from"] for id in tinder_messages}) + list({tinder_messages[id]["to"] for id in tinder_messages}) #TODO from | to
    no_chat_users = [id for id in tinder_matches if id not in users_with_messages]
    no_chat_ghosted_users = [id for id in ghosted_users if id in no_chat_users]

    dumps(unpaired_users, "Unpaired users:")
    dumps(ghosted_users, "Ghosted users:")
    dumps(no_chat_users, "No chat users:")
    dumps(no_chat_ghosted_users, "No chat, ghosted users:")

    for user in no_chat_ghosted_users:
        paired_user = paired_users[user]
        print("User {} was ghosted without messages, unpairing".format(user))
        ghosted_users.remove(user)
        paired_users.remove(user)
        paired_users.remove(paired_user)
        unpaired_users.append(user)

    #pair the unpaired users
    while(len(unpaired_users)>=2):
      userA = unpaired_users.pop()
      userB = unpaired_users.pop()

      paired_users[userA] = userB
      paired_users[userB] = userA
      print("Paired {} with {}".format(userA, userB))

    #save the new pairs
    save_paired_users(paired_users)

def forward_messages():
    #get all the tinder data
    tinder_matches, tinder_messages = get_matches_and_messages()

    #read the existing pairs from our file to figure out what is new
    paired_users = get_paired_users() # { person_idA : person_idB }
    unpaired_users = [id for id in tinder_matches if id not in paired_users]
    ghosted_users = [id for id in paired_users if id not in tinder_matches]

    #read the existing sent messages from our file and figure out what needs to be sent
    sent_messages = get_sent_messages() # [ message_id ]
    unsent_messages = [id for id in tinder_messages if id not in sent_messages]

    #send the unsent messages to their pair
    unsendable = 0
    while len(unsent_messages) > unsendable:
      message_id = unsent_messages.pop(0)
      message = tinder_messages[message_id]
      message_from = message["from"]
      message_text = message["message"]
      if message_from == "59c0946bd134935f459928e6":
          #ignore, it is our own message.
          continue
      if message_from not in paired_users:
          #This user is not paired with anyone yet
          unsent_messages.append(message_id)
          unsendable += 1
          continue
      message_to = paired_users[message_from]
      if message_to not in tinder_matches:
          #No longer matched with this pair
          unsent_messages.append(message_id)
          unsendable+=1
          continue
      to_match_id = tinder_matches[message_to]

      result = api.send_msg(to_match_id, message_text)
      print("Send {} to {}".format(message_text, to_match_id), file=open("/home/aaron/Desktop/Tinder/messagelog.txt", "a"))
      dumps(result, "Send message to {}".format(to_match_id))
      if "error" not in result:
          sent_messages.append(message_id)
      else:
          #api call failed?
          unsent_messages.append(message_id)
          unsendable += 1
          continue

    #save the newly sent messages
    save_sent_messages(sent_messages)

    #dump to output so we can see if it is working right
    #dumps(tinder_messages, "Tinder messages:")
    dumps(unpaired_users, "Unpaired users:")
    dumps(ghosted_users, "Ghosted users:")
    dumps(unsent_messages, "Unsent messages:")

def get_paired_users():
    with open("/home/aaron/Desktop/Tinder/paired_users.json") as file:
      paired_users = json.loads('\n'.join(file.readlines()))   # { person_idA : person_idB }
    return paired_users

def save_paired_users(paired_users):
    print(json.dumps(paired_users, indent=4, sort_keys=True), file=open("/home/aaron/Desktop/Tinder/paired_users.json", "w"))

def get_sent_messages():
    with open("/home/aaron/Desktop/Tinder/sent_messages.json") as file:
      sent_messages = json.loads('\n'.join(file.readlines()))   # [ message_id ]
    return sent_messages

def save_sent_messages(sent_messages):
    print(json.dumps(sent_messages, indent=4, sort_keys=True), file=open("/home/aaron/Desktop/Tinder/sent_messages.json", "w"))

def pause(min, max):
    '''
    In order to appear as a real Tinder user using the app...
    When making many API calls, it is important to pause a...
    realistic amount of time between actions to not make Tinder...
    suspicious!
    '''
    nap_length = (max-min) * random.random() + min
    print('Napping for %f seconds...' % nap_length)
    sleep(nap_length)

def dumps(data, msg):
    if data:
        print("{} ({})".format(msg, len(data)))
        print(json.dumps(data, indent=2, sort_keys=True))

if __name__ == '__main__':
    option = sys.argv[1] if len(sys.argv) > 1 else ""
    number = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    if option == "swipe":
        swipe_right(number)
    elif option == "hey":
        start_conversations()
    elif option == "pair":
        pair_users()
    else:
        print("Forward messages")
        forward_messages()
