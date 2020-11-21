import pytz
import telegram
from datetime import datetime
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from faunadb import query as q
from faunadb.objects import Ref
from faunadb.client import FaunaClient

telegram_bot_token = "your-telegram-token"
fauna_secret = "your-secret-here"

updater = Updater(token=telegram_bot_token, use_context=True)
dispatcher = updater.dispatcher
client = FaunaClient(secret=fauna_secret)


def start(update, context):
    chat_id = update.effective_chat.id
    first_name = update["message"]["chat"]["first_name"]
    username = update["message"]["chat"]["username"]

    try:
        client.query(q.get(q.match(q.index("users"), chat_id)))
    except:
        user = client.query(q.create(q.collection("users"), {
            "data": {
                "id": chat_id,
                "first_name": first_name,
                "username": username,
                "last_command": "",
                "date": datetime.now(pytz.UTC)
            }
        }))
    context.bot.send_message(
        chat_id=chat_id, text="Welcome to Fauna TO-DO, your details have been saved 😊\n\nHere are a few commands to guide you\n/add_todo - add a todo task\n/list_todo - list a todo task")


def add_todo(update, context):
    chat_id = update.effective_chat.id

    user = client.query(q.get(q.match(q.index("users"), chat_id)))
    client.query(q.update(q.ref(q.collection("users"), user["ref"].id()), {
                 "data": {"last_command": "add_todo"}}))
    context.bot.send_message(
        chat_id=chat_id, text="Enter the todo task you want to add 😁")


def list_todo(update, context):
    chat_id = update.effective_chat.id

    task_message = ""
    tasks = client.query(q.paginate(q.match(q.index("todo"), chat_id)))
    for i in tasks["data"]:
        task = client.query(q.get(q.ref(q.collection("todo"), i.id())))
        if task["data"]["completed"]:
            task_status = "Completed"
        else:
            task_status = "Not Completed"
        task_message += "{}\nStatus: {}\nUpdate Link: /update_{}\nDelete Link: /delete_{}\n\n".format(
            task["data"]["todo"], task_status, i.id(), i.id())
    if task_message == "":
        task_message = "You have not added any task, do that with /add_todo 😇"
    context.bot.send_message(chat_id=chat_id, text=task_message)


def update_todo(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    todo_id = message.split("_")[1]

    task = client.query(q.get(q.ref(q.collection("todo"), todo_id)))
    if task["data"]["completed"]:
        new_status = False
    else:
        new_status = True
    client.query(q.update(q.ref(q.collection("todo"), todo_id),
                          {"data": {"completed": new_status}}))
    context.bot.send_message(
        chat_id=chat_id, text="Successfully updated todo task status 👌\n\nSee all your todo with /list_todo")


def delete_todo(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text
    todo_id = message.split("_")[1]

    client.query(q.delete(q.ref(q.collection("todo"), todo_id)))
    context.bot.send_message(
        chat_id=chat_id, text="Successfully deleted todo task status 👌\n\nAdd a new todo with /add_todo")


def echo(update, context):
    chat_id = update.effective_chat.id
    message = update.message.text

    user = client.query(q.get(q.match(q.index("users"), chat_id)))
    last_command = user["data"]["last_command"]

    if last_command == "add_todo":
        todo = client.query(q.create(q.collection("todo"), {
            "data": {
                "user_id": chat_id,
                "todo": message,
                "completed": False,
                "date": datetime.now(pytz.UTC)
            }
        }))
        client.query(q.update(q.ref(q.collection("users"), user["ref"].id()), {
                     "data": {"last_command": ""}}))
        context.bot.send_message(
            chat_id=chat_id, text="Successfully added todo task 👍\n\nSee all your todo with /list_todo")


dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("add_todo", add_todo))
dispatcher.add_handler(CommandHandler("list_todo", list_todo))
dispatcher.add_handler(MessageHandler(
    Filters.regex("/update_[0-9]*"), update_todo))
dispatcher.add_handler(MessageHandler(
    Filters.regex("/delete_[0-9]*"), delete_todo))
dispatcher.add_handler(MessageHandler(Filters.text, echo))
updater.start_polling()
