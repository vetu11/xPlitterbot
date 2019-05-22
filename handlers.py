# coding=utf-8
# Archivo: handlers
# Descripción: Aquí se declararán los handlers a las distintas llamadas de la API.

import re
import const
import utils
import random
from math import ceil
from lang import get_lang

from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle,\
    InputTextMessageContent, ForceReply, Bot, Update, ChatAction
from telegram.ext import run_async
from telegram.error import Unauthorized, BadRequest

from group import Group
from group_manager import group_manager
from user_manager import user_manager
from transaction_manager import transaction_manager

re_amount_comment = re.compile(const.RE_AMOUNT_COMMENT_PATTERN)


def _history_transactions_buttons(transaction_list, page):
    type_to_symbol = {"purchase": "🛒", "transfer": "💸", "debt": "📝"}
    transaction_list = list(transaction_list)
    transaction_list.reverse()
    keyboard = []

    t_min = page * const.TRANSACTIONS_PER_PAGE_HISTORY
    t_max = (page + 1) * const.TRANSACTIONS_PER_PAGE_HISTORY
    if t_max > len(transaction_list):
        t_max = len(transaction_list)

    for transaction in transaction_list[t_min:t_max]:
        button_text = type_to_symbol[transaction.type] + "%s💰 %s\n" % (transaction.amount,
                                                                         transaction.comment[:10])
        keyboard.append([InlineKeyboardButton(button_text, callback_data="tr*%s*%s" % (transaction.id, page))])

    if len(transaction_list) > const.TRANSACTIONS_PER_PAGE_HISTORY:
        last_page = int(ceil(len(transaction_list) / const.TRANSACTIONS_PER_PAGE_HISTORY)) - 1
        prev_page = 0 if page <= 0 else page - 1
        next_page = last_page if page >= last_page else page + 1

        keyboard.append([InlineKeyboardButton("⏪", callback_data="hi*0" if page != 0 else "none"),
                         InlineKeyboardButton("⬅️", callback_data=("hi*%s" % prev_page if prev_page != page else "none")),
                         InlineKeyboardButton("#️⃣", callback_data="none*%s" % page),
                         InlineKeyboardButton("➡️", callback_data=("hi*%s" % next_page) if page != next_page else "none"),
                         InlineKeyboardButton("⏩", callback_data=("hi*%s" % last_page) if page != last_page else "none")])

    return keyboard


def _check_pm_ready(bot, update, lang):
    try:
        bot.send_chat_action(update.effective_user.id, ChatAction.TYPING)
        return True
    except (Unauthorized, BadRequest):
        update.callback_query.answer(lang.get_text("first_pm_the_bot", bot_username=const.aux.bot_username),
                                     show_alert=True)
        return False


def _random_fact(group: Group, lang):

    available_facts = {"fact_0": {"amount": Group.total_spent},
                      "fact_1": {"amount": Group.total_transferred},
                      "fact_2": {"_all": Group.find_most_expensive_purchase},
                      "fact_3": {"name_simple": Group.find_user_in_most_purchases_as_participant},
                      "fact_4": {"name_simple": Group.find_user_in_most_purchases_as_buyer}}

    while available_facts:
        chosen_fact = random.choice([k for k in available_facts])
        atributes = {}
        is_available = True

        for k in available_facts[chosen_fact]:
            if k != "_all":
                atributes[k] = available_facts[chosen_fact][k](group)
                if atributes[k] is False:
                    is_available = False
            else:
                result = available_facts[chosen_fact][k](group)
                atributes.update(result)
                if result is False:
                    is_available = False

        if is_available:
            break
        else:
            available_facts.pop(chosen_fact)

    if available_facts:
        return lang.get_text(chosen_fact, **atributes)
    else:
        return ""


def generic_message(bot, update, text_code):
    # Responde a cualquier mensaje con un texto genérico, sin añadiduras.

    message = update.effective_message
    user = update.effective_user
    user_lang_code = user.language_code
    lang = get_lang(user_lang_code)

    message.reply_text(lang.get_text(text_code), parse_mode=ParseMode.MARKDOWN, reply=False)


# The basics
def start(bot, update, args):
    # Responde al comando "/start"
    if args:
        if args[0] == "help":
            help(bot, update)
            return
    generic_message(bot, update, "start")


def help(bot, update):
    # Responde al comando "/help"

    generic_message(bot, update, "help")


def more(bot, update):
    # Responde al comando "/more"

    generic_message(bot, update, "more")


def donate(bot, update):
    # Responde al comando "/donate"

    generic_message(bot, update, "donate")


def error_handler(bot, update, telegram_error):
    bot.send_message(const.VETU_ID, "ERROR:\nUpdate:\n" + str(update) + "\ntelegram_error:\n" + telegram_error)


# Bot Commands
def add(bot, update, args, chat_data, user_data):
    # Pide más datos o crea una transacción con los datos proporcionados.
    group = group_manager.get_group(update.effective_chat, chat_data)
    group.add_telegram_user(update.effective_user)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)

    if args:
        if re_amount_comment.match(utils.join_unicode_list(args, " ")):
            select_transaction_type_group(bot, update, user_data)
            return
    update.effective_message.reply_text(lang.get_text("add_message"),
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=ForceReply(selective=True))


@run_async
def split(bot:  Bot, update, chat_data, user_data):
    """/split command response."""

    group = group_manager.get_group(update.effective_chat, chat_data)
    group.add_telegram_user(update.effective_user)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)

    fact = _random_fact(group, lang)

    # Phase 1, calculate ledger
    our_message = update.effective_message.reply_text(lang.get_text("split_phase_1_calculating", fact=fact),
                                                      parse_mode=ParseMode.MARKDOWN)
    bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    group.calculate_ledger()

    ledger_text = ""

    for member_id in group.ledger:
        ledger_text += "" + user_manager.get_user_by_id(member_id).full_name + " " + \
                       str(group.ledger[member_id]) + "💰\n"

    # Phase 2, calculate movements
    our_message.edit_text(lang.get_text("split_phase_2_calculating", ledger=ledger_text, fact=fact),
                          parse_mode=ParseMode.MARKDOWN,
                          disable_web_page_preview=True)
    bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    best_movents = group.calculate_best_movements()

    movements_text = ""

    for movement in best_movents:
        movements_text += user_manager.get_user_by_id(movement[0]).full_name + " ----> " + \
            user_manager.get_user_by_id(movement[1]).full_name + " %s 💰\n" % abs(movement[2])

    keyboard = [[InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

    our_message.edit_text(lang.get_text("split_results",
                                        ledger=ledger_text,
                                        movements=movements_text,
                                        fact=fact),
                          parse_mode=ParseMode.MARKDOWN,
                          disable_web_page_preview=True,
                          reply_markup=InlineKeyboardMarkup(keyboard))


def introduce(bot, update: Update, chat_data, user_data):
    """This command is for intrdoucing new people to the bot. Basically, to make sure they are added to the group,
    so they can be selected when creating a transaction. User should use this command replying the message
    of other user."""

    group = group_manager.get_group(update.effective_chat, chat_data)
    group.add_telegram_user(update.effective_user)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)

    keyboard = [[InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

    if update.effective_message.reply_to_message is None:
        update.effective_message.reply_text(lang.get_text("introduce_error_need_reply"),
                                            quote=False,
                                            parse_mode=ParseMode.MARKDOWN,
                                            disable_web_page_preview=True,
                                            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    target_user = group.add_telegram_user(update.effective_message.reply_to_message.from_user)

    update.effective_message.reply_text(lang.get_text("introduce", target_user_name=target_user.full_name),
                                        quote=False,
                                        parse_mode=ParseMode.MARKDOWN,
                                        disable_web_page_preview=True,
                                        reply_markup=InlineKeyboardMarkup(keyboard))


def history_group(bot, update: Update, chat_data, user_data):
    """/history command. resumes the last transactions."""

    group = group_manager.get_group(update.effective_chat, chat_data)
    group.add_telegram_user(update.effective_user)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)

    # Page can only be known if this is a inline_callback, else this is the first message.
    if update.callback_query is not None:
        page = int(update.callback_query.data.split("*")[1])
        method = update.effective_message.edit_text
    else:
        page = 0
        method = update.effective_message.reply_text

    keyboard = _history_transactions_buttons(group.transaction_list, page)
    keyboard.append([InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")])

    if len(group.transaction_list) > 0:
        method(text=lang.get_text("history_group"),
               parse_mode=ParseMode.MARKDOWN,
               disable_web_page_preview=True,
               reply_markup=InlineKeyboardMarkup(keyboard))
        return
    else:
        keyboard = [[InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]
        method(text=lang.get_text("history_empty"),
               parse_mode=ParseMode.MARKDOWN,
               disable_web_page_preview=True,
               reply_markup=InlineKeyboardMarkup(keyboard))


def force_save(bot, update):
    if int(update.effective_user.id) != const.VETU_ID:
        return

    user_manager.save()
    transaction_manager.save()
    group_manager.save()

    update.effective_message.reply_text("Guardado.")


def auto_save(*args, **kwargs):
    """Called with the interval defined on bot.py, or when the bot is stopping"""

    user_manager.save()
    transaction_manager.save()
    group_manager.save()


# Other Messages
def new_members(bot, update, chat_data):
    # Cuando se añaden nuevos usuarios al grupo los añade a la instancia del grupo correspondiente. Si se ha añadido
    # al bot enviará un mensaje presentandose.

    t_users = update.effective_message.new_chat_members
    bot_id = const.aux.bot_id
    new_group = False
    group = group_manager.get_group(update.effective_chat, chat_data)
    lang = get_lang(group.lang)

    for user in t_users:
        if user.id == bot_id:
            new_group = True
        else:
            group.add_telegram_user(update.effective_user)

    if new_group:
        keyboard = [[InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

        update.effective_message.reply_text(lang.get_text("new_group"),
                                            reply_markup=InlineKeyboardMarkup(keyboard),
                                            reply=False,
                                            parse_mode=ParseMode.MARKDOWN)


def select_transaction_type_group(bot, update, user_data):
    # Este método se ejecutará cuando el bot reciba un mensaje con el formato "<cantidad> <comentario>", que
    # deberia ser una contestación al mensaje de new_members, cuando reciba el comando /add.

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)

    txt = update.effective_message.text
    if "/add" in txt:
        txt = utils.join_unicode_list(txt.split()[1:], space=" ")
    amount = txt.split()[0]
    comment = txt.replace(amount + " ", "")
    amount = float(amount.replace(",", "."))

    keyboard = [[InlineKeyboardButton(lang.get_text("purchase"), callback_data=("n_pur*%s*%s" % (amount,
                                                                                                 comment))[:64]),
                 InlineKeyboardButton(lang.get_text("transfer"), callback_data=("n_tra*%s*%s" % (amount,
                                                                                                 comment))[:64]),
                 InlineKeyboardButton(lang.get_text("debt"), callback_data=("n_dbt*%s*%s" % (amount, comment))[:64])],
                [InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

    update.effective_message.reply_text(lang.get_text("select_transaction_type_message",
                                                      amount=amount,
                                                      comment=comment),
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=InlineKeyboardMarkup(keyboard))


def select_transaction_type_pm(bot, update, user_data):
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)

    # We need to know what group is refering the user, if we don't know this may be an error due to a server restart.
    if "editing" not in user_data:
        return

    txt = update.effective_message.text
    if "/add" in txt:
        txt = txt.replace("/add ", "")
    amount = txt.split()[0]
    comment = txt.replace(str(amount) + " ", "")

    keyboard = [[InlineKeyboardButton(lang.get_text("purchase"), callback_data=("n_pur*%s*%s" % (amount,
                                                                                                 comment))[:64]),
                 InlineKeyboardButton(lang.get_text("transfer"), callback_data=("n_tra*%s*%s" % (amount,
                                                                                                 comment))[:64]),
                 InlineKeyboardButton(lang.get_text("debt"), callback_data=("n_dbt*%s*%s" % (amount, comment))[:64])]]

    update.effective_message.reply_text(lang.get_text("select_transaction_type_message",
                                                      amount=amount,
                                                      comment=comment),
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=InlineKeyboardMarkup(keyboard))


def message(bot, update, chat_data):
    # Se ejecuta cuando recibe un mensaje cualquiera que no haya pasado los filtros, sólo para debugging.
    pass
    # print(update.effective_message.text)


# Inline buttons
def none(bot, update):
    # Para los botones que no debería hacer nada o simplemente mostrar un texto en pantalla.

    text = update.callback_query.data.split("*")[1] if len(update.callback_query.data.split("*")) > 1 else ""

    update.callback_query.answer(text)


def hi_button(bot, update, chat_data, user_data):
    # Para el botón en el que los usuarios se presentan al bot para ser añadidos al grupo.

    group = group_manager.get_group(update.effective_chat, chat_data)
    user = user_manager.get_user(update.effective_user, user_data)
    group.add_telegram_user(update.effective_user)
    lang = get_lang(user.language_code)

    update.callback_query.answer(lang.get_text("hi",
                                               user_full_name_simple=user.full_name_simple,
                                               group_name=update.effective_chat.title))


def transaction_info(bot, update: Update, chat_data, user_data):

    group = group_manager.get_group(update.effective_chat, chat_data)
    group.add_telegram_user(update.effective_user)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    transaction_id, page = update.callback_query.data.split("*")[1:]
    transaction = transaction_manager.get_transaction_by_id(transaction_id)
    page = int(page)

    if transaction.type == "purchase":
        participants_text = lang.enum([user_manager.get_user_by_id(x).full_name for x in transaction.participants])

        text = lang.get_text("purchase_info",
                             comment=transaction.comment,
                             amount=transaction.amount,
                             buyer=user_manager.get_user_by_id(transaction.buyer).full_name,
                             participants=participants_text)
    elif transaction.type == "transfer":
        text = lang.get_text("transfer_info",
                             comment=transaction.comment,
                             amount=transaction.amount,
                             payer=user_manager.get_user_by_id(transaction.payer).full_name,
                             receiver=user_manager.get_user_by_id(transaction.receiver).full_name)
    else:
        text = lang.get_text("debt_info",
                             comment=transaction.comment,
                             amount=transaction.amount,
                             lender=user_manager.get_user_by_id(transaction.lender).full_name,
                             debtor=user_manager.get_user_by_id(transaction.debtor).full_name)

    keyboard = [[InlineKeyboardButton(lang.get_text("go_back"), callback_data="hi*%s" % page),
                 InlineKeyboardButton(lang.get_text("delete"), callback_data="del_tr*%s" % transaction_id)]]

    update.effective_message.edit_text(text,
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True,
                                       reply_markup=InlineKeyboardMarkup(keyboard))


def delete_transaction(bot, update, user_data, chat_data):
    group = group_manager.get_group(update.effective_chat, chat_data)
    group.add_telegram_user(update.effective_user)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    transaction_id = update.callback_query.data.split("*")[1]
    transaction = transaction_manager.get_transaction_by_id(transaction_id)

    group_manager.get_group_by_id(transaction.group_id).remove_transaction(transaction_id)
    if transaction.type == "purchase":
        user_manager.get_user_by_id(transaction.buyer).remove_transaction(transaction_id)
        for user_id in transaction.participants:
            user_manager.get_user_by_id(user_id).remove_transaction(transaction_id)
    elif transaction.type == "transfer":
        user_manager.get_user_by_id(transaction.payer).remove_transaction(transaction_id)
        user_manager.get_user_by_id(transaction.receiver).remove_transaction(transaction_id)
    else:
        user_manager.get_user_by_id(transaction.lender).remove_transaction(transaction_id)
        user_manager.get_user_by_id(transaction.debtor).remove_transaction(transaction_id)
    transaction_manager.remove_transaction(transaction_id)

    keyboard = [[InlineKeyboardButton(lang.get_text("go_back"), callback_data="hi*0")]]

    update.effective_message.edit_text(lang.get_text("transaction_deleted"),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True,
                                       reply_markup=InlineKeyboardMarkup(keyboard))


def new_purchase(bot: Bot, update, chat_data, user_data):
    # Para el botón de añadir una compra, mostrado en el mensaje de saludo (new_members) y en otros mensajes.

    if update.effective_chat.type == "private":
        # If "editing" it's not in user_data, we're here by an error we can't solve.
        if "editing" not in user_data:
            update.effective_message.edit_reply_markup(InlineKeyboardMarkup([[]]))
            return
        group = group_manager.get_group_by_id(user_data["editing"])
        update.effective_message.delete()
    else:
        group = group_manager.get_group(update.effective_chat, chat_data)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    amount, comment = data.split("*")[1:]

    if not _check_pm_ready(bot, update, lang):
        return

    purchase = transaction_manager.add_transaction(transaction_type="purchase",
                                                   amount=float(amount),
                                                   comment=comment,
                                                   buyer=user.id,
                                                   participants=[x.id for x in group.user_list],
                                                   group_id=group.id)

    group.add_telegram_user(update.effective_user)

    # Mensaje al grupo
    if update.effective_chat.type != "private":
        keyboard = [[InlineKeyboardButton(lang.get_text("goto_pm"), url="t.me/%s" % const.aux.bot_username)],
                    [InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

        update.effective_message.edit_text(lang.get_text("goto_pm_message", bot_username=const.aux.bot_username),
                                           parse_mode=ParseMode.MARKDOWN,
                                           reply_markup=InlineKeyboardMarkup(keyboard),
                                           disable_web_page_preview=True)

    # Mensaje PM
    keyboard = []
    for participant in group.user_list[:5]:
        text = "⚪️ " if participant.id != purchase.buyer else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + participant.full_name_simple,
                                              callback_data="n_pur_bu_sel*%d*0*%s" % (participant.id,
                                                                                        purchase.id))])
    if len(group.user_list) > const.USERS_PER_PAGE_NEW_TRANSACTION:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_pur_bu_p*0*%s" % purchase.id),
                         InlineKeyboardButton("⬅️", callback_data="n_pur_bu_p*0*%s" % purchase.id),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=0)),
                         InlineKeyboardButton("➡️", callback_data="n_pur_bu_p*1*%s" % purchase.id),
                         InlineKeyboardButton("⏩", callback_data="n_pur_bu_p*%d*%s" %
                                                                 (int(ceil(len(group.user_list) / 5.0)), purchase.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_pur_pa_p*0*%s" % purchase.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % purchase.id)])

    bot.send_message(chat_id=user.id,
                     text=lang.get_text("select_buyer", buyer=user_manager.get_user_by_id(purchase.buyer).full_name),
                     reply_markup=InlineKeyboardMarkup(keyboard),
                     parse_mode=ParseMode.MARKDOWN,
                     disable_web_page_preview=True)


def new_purchase_buyer(bot, update, user_data):
    # Para seleccionar el comprador de la transacción que se señala en callba_query.data

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    cmd = data.split("*")[0]

    if cmd == "n_pur_bu_p":
        page, transaction_id = data.split("*")[1:]
        purchase = transaction_manager.get_transaction_by_id(transaction_id)
    elif cmd == "n_pur_bu_sel":
        buyer_id, page, transaction_id = data.split("*")[1:]
        purchase = transaction_manager.get_transaction_by_id(transaction_id)
        if purchase.buyer == int(buyer_id):
            update.callback_query.answer()
            return
        purchase.set_buyer(int(buyer_id))
    else:
        print("wtf es %s" % cmd)
        return
    page = int(page)

    group = group_manager.get_group_by_id(purchase.group_id)

    keyboard = []
    for member in group.user_list[5 * page:5 + 5 * page]:
        text = "⚪️ " if member.id != purchase.buyer else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + member.full_name_simple,
                                              callback_data="n_pur_bu_sel*%d*%d*%s" % (member.id,
                                                                                       page,
                                                                                       purchase.id))])
    if len(group.user_list) > const.USERS_PER_PAGE_NEW_TRANSACTION:
        last_page = int(ceil(len(group.user_list) / const.USERS_PER_PAGE_NEW_TRANSACTION)) - 1
        next_page = last_page if page >= last_page else page + 1
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_pur_bu_p*0*%s" % purchase.id),
                         InlineKeyboardButton("⬅️", callback_data="n_pur_bu_p*%d*%s" % (0 if page <= 0 else page - 1,
                                                                                        purchase.id)),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=page)),
                         InlineKeyboardButton("➡️", callback_data="n_pur_bu_p*%d*%s" % (next_page, purchase.id)),
                         InlineKeyboardButton("⏩", callback_data="n_pur_bu_p*%d*%s" % (last_page, purchase.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_pur_pa_p*0*%s" % purchase.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % purchase.id)])

    update.effective_message.edit_text(text=lang.get_text("select_buyer",
                                                          buyer=user_manager.get_user_by_id(purchase.buyer).full_name),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)


def new_purchase_participants(bot, update, user_data):
    # Para seleccionar los participantes de la compra señalada en callback_query.data

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    cmd = data.split("*")[0]

    if cmd == "n_pur_pa_p":
        page, transaction_id = data.split("*")[1:]
        purchase = transaction_manager.get_transaction_by_id(transaction_id)
    elif cmd == "n_pur_pa_sel":
        participant_id, page, transaction_id = data.split("*")[1:]
        purchase = transaction_manager.get_transaction_by_id(transaction_id)
        purchase.add_remove_participant(int(participant_id))
    else:
        print("wtf es %s" % cmd)
        return
    page = int(page)

    group = group_manager.get_group_by_id(purchase.group_id)
    last_page = int(ceil(len(group.user_list) / 5.0)) - 1
    next_page = last_page if page >= last_page else page + 1

    keyboard = []
    for member in group.user_list[5 * page:5 + 5 * page]:
        text = "❎ " if member.id not in purchase.participants else "☑️ "
        keyboard.append([InlineKeyboardButton(text + member.full_name_simple,
                                              callback_data="n_pur_pa_sel*%d*%d*%s" % (member.id,
                                                                                       page,
                                                                                       purchase.id))])

    if len(group.user_list) > 5:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_pur_pa_p*0*%s" % purchase.id),
                         InlineKeyboardButton("⬅️", callback_data="n_pur_pa_p*%d*%s" % (0 if page <= 0 else page - 1,
                                                                                        purchase.id)),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=page)),
                         InlineKeyboardButton("➡️", callback_data="n_pur_pa_p*%d*%s" % (next_page, purchase.id)),
                         InlineKeyboardButton("⏩", callback_data="n_pur_pa_p*%d*%s" % (last_page, purchase.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_pur_res*%s" % purchase.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % purchase.id)])

    participant_name_list = [user_manager.get_user_by_id(x).full_name for x in purchase.participants]

    update.effective_message.edit_text(text=lang.get_text("select_participants",
                                                          buyer=user_manager.get_user_by_id(purchase.buyer).full_name,
                                                          participants=lang.enum(participant_name_list)),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)


# Resume with the details of the just added purchase.
def new_purchase_resume(bot, update, user_data):
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    purchase_id = data.split("*")[1]
    purchase = transaction_manager.get_transaction_by_id(purchase_id)
    buyer = user_manager.get_user_by_id(purchase.buyer)
    participants = [user_manager.get_user_by_id(x) for x in purchase.participants]
    participants_text = lang.enum([x.full_name for x in participants])

    if not participants:
        update.callback_query.answer(lang.get_text("new_purchase_resume_error_not_0"))
        return

    group_manager.get_group_by_id(purchase.group_id).add_transaction(purchase)
    buyer.add_transaction(purchase)
    for user_id in purchase.participants:
        user_manager.get_user_by_id(user_id).add_transaction(purchase)

    keyboard = [[]]

    group_title = group_manager.get_group_by_id(purchase.group_id).title

    update.effective_message.edit_text(text=lang.get_text("new_purchase_resume",
                                                          amount=purchase.amount,
                                                          comment=purchase.comment,
                                                          buyer=buyer.full_name,
                                                          participants=participants_text,
                                                          title=group_title),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)

    user_data["editing"] = purchase.group_id


def new_transfer(bot, update, chat_data, user_data):
    """Transaction type selected as transfer by the user. Now it haves to select payer."""
    if update.effective_chat.type == "private":
        # If "editing" it's not in user_data, we're here by an error we can't solve.
        if "editing" not in user_data:
            update.effective_message.edit_reply_markup(InlineKeyboardMarkup([[]]))
            return
        group = group_manager.get_group_by_id(user_data["editing"])
        update.effective_message.delete()
    else:
        group = group_manager.get_group(update.effective_chat, chat_data)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    amount, comment = data.split("*")[1:]

    if not _check_pm_ready(bot, update, lang):
        return

    transfer = transaction_manager.add_transaction(transaction_type="transfer",
                                                   amount=float(amount),
                                                   comment=comment,
                                                   payer=user.id,
                                                   reciver=None,
                                                   group_id=group.id)

    group.add_telegram_user(update.effective_user)

    # Group message
    if update.effective_chat.type != "private":
        keyboard = [[InlineKeyboardButton(lang.get_text("goto_pm"), url="t.me/%s" % const.aux.bot_username)],
                    [InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

        update.effective_message.edit_text(lang.get_text("goto_pm_message", bot_username=const.aux.bot_username),
                                           parse_mode=ParseMode.MARKDOWN,
                                           reply_markup=InlineKeyboardMarkup(keyboard),
                                           disable_web_page_preview=True)

    # Private message
    keyboard = []
    for participant in group.user_list[:5]:
        text = "⚪️ " if participant.id != transfer.payer else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + participant.full_name_simple,
                                              callback_data="n_tra_pa_sel*%d*0*%s" % (participant.id,
                                                                                      transfer.id))])
    if len(group.user_list) > const.USERS_PER_PAGE_NEW_TRANSACTION:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_tra_pa_p*0*%s" % transfer.id),
                         InlineKeyboardButton("⬅️", callback_data="n_tra_pa_p*0*%s" % transfer.id),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=0)),
                         InlineKeyboardButton("➡️", callback_data="n_tra_pa_p*1*%s" % transfer.id),
                         InlineKeyboardButton("⏩", callback_data="n_tra_pa_p*%d*%s" %
                                                                 (int(ceil(len(group.user_list) / 5.0)), transfer.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_tra_re_p*0*%s" % transfer.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % transfer.id)])

    bot.send_message(chat_id=user.id,
                     text=lang.get_text("select_payer", payer=user_manager.get_user_by_id(transfer.payer).full_name),
                     reply_markup=InlineKeyboardMarkup(keyboard),
                     parse_mode=ParseMode.MARKDOWN,
                     disable_web_page_preview=True)


def new_transfer_payer(bot, update, user_data):
    """Payer or page selected on the new_transfer_payer menu"""

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    cmd = data.split("*")[0]

    if cmd == "n_tra_pa_p":
        page, transaction_id = data.split("*")[1:]
        transfer = transaction_manager.get_transaction_by_id(transaction_id)
    elif cmd == "n_tra_pa_sel":
        payer_id, page, transaction_id = data.split("*")[1:]
        transfer = transaction_manager.get_transaction_by_id(transaction_id)
        if transfer.payer == int(payer_id):
            update.callback_query.answer()
            return
        transfer.set_payer(int(payer_id))
    else:
        print("wtf es %s" % cmd)
        return
    page = int(page)

    group = group_manager.get_group_by_id(transfer.group_id)
    last_page = int(ceil(len(group.user_list) / 5.0)) - 1
    next_page = last_page if page >= last_page else page + 1

    keyboard = []
    for member in group.user_list[5 * page:5 + 5 * page]:
        text = "⚪️ " if member.id != transfer.payer else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + member.full_name_simple,
                                              callback_data="n_tra_pa_sel*%d*%d*%s" % (member.id,
                                                                                       page,
                                                                                       transfer.id))])
    if len(group.user_list) > 5:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_tra_pa_p*0*%s" % transfer.id),
                         InlineKeyboardButton("⬅️", callback_data="n_tra_pa_p*%d*%s" % (0 if page <= 0 else page - 1,
                                                                                        transfer.id)),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=page)),
                         InlineKeyboardButton("➡️", callback_data="n_tra_pa_p*%d*%s" % (next_page, transfer.id)),
                         InlineKeyboardButton("⏩", callback_data="n_tra_pa_p*%d*%s" % (last_page, transfer.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_tra_re_p*0*%s" % transfer.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % transfer.id)])

    update.effective_message.edit_text(text=lang.get_text("select_payer",
                                                          payer=user_manager.get_user_by_id(transfer.payer).full_name),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)


def new_transfer_receiver(bot, update, user_data):
    """After selecting a payer fore the transfer, the user must select a receiver. This is where that shit happens."""

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    cmd = data.split("*")[0]

    if cmd == "n_tra_re_p":
        page, transaction_id = data.split("*")[1:]
        transfer = transaction_manager.get_transaction_by_id(transaction_id)
    elif cmd == "n_tra_re_sel":
        receiver_id, page, transaction_id = data.split("*")[1:]
        transfer = transaction_manager.get_transaction_by_id(transaction_id)
        transfer.set_receiver(int(receiver_id))
    else:
        print("wtf es %s" % cmd)
        return
    page = int(page)

    group = group_manager.get_group_by_id(transfer.group_id)
    last_page = int(ceil(len(group.user_list) / 5.0)) - 1
    next_page = last_page if page >= last_page else page + 1

    keyboard = []
    for member in group.user_list[5 * page:5 + 5 * page]:
        text = "⚪️" if member.id != transfer.receiver else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + member.full_name_simple,
                                              callback_data="n_tra_re_sel*%d*%d*%s" % (member.id,
                                                                                       page,
                                                                                       transfer.id))])

    if len(group.user_list) > 5:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_tra_re_p*0*%s" % transfer.id),
                         InlineKeyboardButton("⬅️", callback_data="n_tra_re_p*%d*%s" % (0 if page <= 0 else page - 1,
                                                                                        transfer.id)),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=page)),
                         InlineKeyboardButton("➡️", callback_data="n_tra_re_p*%d*%s" % (next_page, transfer.id)),
                         InlineKeyboardButton("⏩", callback_data="n_tra_re_p*%d*%s" % (last_page, transfer.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_tra_res*%s" % transfer.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % transfer.id)])

    receiver = user_manager.get_user_by_id(transfer.receiver).full_name if transfer.receiver is not None else ""

    update.effective_message.edit_text(text=lang.get_text("select_receiver",
                                                          amount=transfer.amount,
                                                          payer=user_manager.get_user_by_id(transfer.payer).full_name,
                                                          receiver=receiver),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)


def new_transfer_resume(bot, update, user_data):
    """Final message of the new_transfer series. A message resuming the new created transfer."""

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    transfer_id = data.split("*")[1]
    transfer = transaction_manager.get_transaction_by_id(transfer_id)
    payer = user_manager.get_user_by_id(transfer.payer)
    receiver = user_manager.get_user_by_id(transfer.receiver)

    if not receiver:
        update.callback_query.answer(lang.get_text("new_transfer_resume_error_need_receiver"))
        return

    group_manager.get_group_by_id(transfer.group_id).add_transaction(transfer)
    payer.add_transaction(transfer)
    receiver.add_transaction(transfer)

    keyboard = [[]]

    update.effective_message.edit_text(text=lang.get_text("new_transfer_resume",
                                                          amount=transfer.amount,
                                                          comment=transfer.comment,
                                                          payer=payer.full_name,
                                                          receiver=receiver.full_name,
                                                          title=group_manager.get_group_by_id(transfer.group_id).title),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)

    user_data["editing"] = transfer.group_id


def new_debt(bot, update, chat_data, user_data):
    """Transaction type selected as debt by the user. Now it haves to select payer."""
    if update.effective_chat.type == "private":
        # If "editing" it's not in user_data, we're here by an error we can't solve.
        if "editing" not in user_data:
            update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[]]))
            return
        group = group_manager.get_group_by_id(user_data["editing"])
        update.effective_message.delete()
    else:
        group = group_manager.get_group(update.effective_chat, chat_data)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    amount, comment = data.split("*")[1:]

    if not _check_pm_ready(bot, update, lang):
        return

    debt = transaction_manager.add_transaction(transaction_type="debt",
                                               amount=float(amount),
                                               comment=comment,
                                               lender=user.id,
                                               debtor=None,
                                               group_id=group.id)

    group.add_telegram_user(update.effective_user)

    # Group message
    if update.effective_chat.type != "private":
        keyboard = [[InlineKeyboardButton(lang.get_text("goto_pm"), url="t.me/%s" % const.aux.bot_username)],
                    [InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

        update.effective_message.edit_text(lang.get_text("goto_pm_message", bot_username=const.aux.bot_username),
                                           parse_mode=ParseMode.MARKDOWN,
                                           reply_markup=InlineKeyboardMarkup(keyboard),
                                           disable_web_page_preview=True)

    # Private message
    keyboard = []
    for member in group.user_list[:5]:
        text = "⚪️ " if member.id != debt.lender else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + member.full_name_simple,
                                              callback_data="n_dbt_le_sel*%d*0*%s" % (member.id,
                                                                                      debt.id))])
    if len(group.user_list) > const.USERS_PER_PAGE_NEW_TRANSACTION:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_dbt_le_p*0*%s" % debt.id),
                         InlineKeyboardButton("⬅️", callback_data="n_dbt_le_p*0*%s" % debt.id),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=0)),
                         InlineKeyboardButton("➡️", callback_data="n_dbt_le_p*1*%s" % debt.id),
                         InlineKeyboardButton("⏩", callback_data="n_dbt_le_p*%d*%s" %
                                                                 (int(ceil(len(group.user_list) / 5.0)), debt.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_dbt_de_p*0*%s" % debt.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % debt.id)])

    bot.send_message(chat_id=user.id,
                     text=lang.get_text("select_lender",
                                        amount=debt.amount,
                                        lender=user_manager.get_user_by_id(debt.lender).full_name),
                     reply_markup=InlineKeyboardMarkup(keyboard),
                     parse_mode=ParseMode.MARKDOWN,
                     disable_web_page_preview=True)


def new_debt_lender(bot, update, user_data):
    """First phase of the debt creation. In this message the user must select a lender."""

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    cmd = data.split("*")[0]

    if cmd == "n_dbt_le_p":
        page, transaction_id = data.split("*")[1:]
        debt = transaction_manager.get_transaction_by_id(transaction_id)
    elif cmd == "n_dbt_le_sel":
        lender_id, page, transaction_id = data.split("*")[1:]
        debt = transaction_manager.get_transaction_by_id(transaction_id)
        if debt.lender == int(lender_id):
            update.callback_query.answer()
            return
        debt.set_lender(int(lender_id))
    else:
        print("wtf es %s" % cmd)
        return
    page = int(page)

    group = group_manager.get_group_by_id(debt.group_id)
    last_page = int(ceil(len(group.user_list) / 5.0)) - 1
    next_page = last_page if page >= last_page else page + 1

    keyboard = []
    for member in group.user_list[5 * page:5 + 5 * page]:
        text = "⚪️ " if member.id != debt.lender else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + member.full_name_simple,
                                              callback_data="n_dbt_le_sel*%d*%d*%s" % (member.id,
                                                                                       page,
                                                                                       debt.id))])
    if len(group.user_list) > 5:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_dbt_le_p*0*%s" % debt.id),
                         InlineKeyboardButton("⬅️", callback_data="n_dbt_le_p*%d*%s" % (0 if page <= 0 else page - 1,
                                                                                        debt.id)),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=page)),
                         InlineKeyboardButton("➡️", callback_data="n_dbt_le_p*%d*%s" % (next_page, debt.id)),
                         InlineKeyboardButton("⏩", callback_data="n_dbt_le_p*%d*%s" % (last_page, debt.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_dbt_de_p*0*%s" % debt.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % debt.id)])

    update.effective_message.edit_text(text=lang.get_text("select_lender",
                                                          amount=debt.amount,
                                                          lender=user_manager.get_user_by_id(debt.lender).full_name),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)


def new_debt_debtor(bot, update, user_data):
    """After selecting a lender for the transfer, the user must select a debtor. This is where that shit happens."""

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    cmd = data.split("*")[0]

    if cmd == "n_dbt_de_p":
        page, transaction_id = data.split("*")[1:]
        debt = transaction_manager.get_transaction_by_id(transaction_id)
    elif cmd == "n_dbt_de_sel":
        participant_id, page, transaction_id = data.split("*")[1:]
        debt = transaction_manager.get_transaction_by_id(transaction_id)
        debt.set_debtor(int(participant_id))
    else:
        print("wtf es %s" % cmd)
        return
    page = int(page)

    group = group_manager.get_group_by_id(debt.group_id)
    last_page = int(ceil(len(group.user_list) / 5.0)) - 1
    next_page = last_page if page >= last_page else page + 1

    keyboard = []
    for member in group.user_list[5 * page:5 + 5 * page]:
        text = "⚪️" if member.id != debt.debtor else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + member.full_name_simple,
                                              callback_data="n_dbt_de_sel*%d*%d*%s" % (member.id,
                                                                                       page,
                                                                                       debt.id))])

    if len(group.user_list) > 5:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_dbt_de_p*0*%s" % debt.id),
                         InlineKeyboardButton("⬅️", callback_data="n_dbt_de_p*%d*%s" % (0 if page <= 0 else page - 1,
                                                                                        debt.id)),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=page)),
                         InlineKeyboardButton("➡️", callback_data="n_dbt_de_p*%d*%s" % (next_page, debt.id)),
                         InlineKeyboardButton("⏩", callback_data="n_dbt_de_p*%d*%s" % (last_page, debt.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_dbt_res*%s" % debt.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="n_trc_c*%s" % debt.id)])

    debtor = user_manager.get_user_by_id(debt.debtor).full_name if debt.debtor is not None else ""

    update.effective_message.edit_text(text=lang.get_text("select_debtor",
                                                          amount=debt.amount,
                                                          lender=user_manager.get_user_by_id(debt.lender).full_name,
                                                          debtor=debtor),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)


def new_debt_resume(bot, update, user_data):
    """Final message of the new_debt series. A message resuming the new created debt."""

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    transfer_id = data.split("*")[1]
    debt = transaction_manager.get_transaction_by_id(transfer_id)
    lender = user_manager.get_user_by_id(debt.lender)
    debtor = user_manager.get_user_by_id(debt.debtor)

    if not debtor:
        update.callback_query.answer(lang.get_text("new_transfer_resume_error_need_receiver"))
        return

    group_manager.get_group_by_id(debt.group_id).add_transaction(debt)
    lender.add_transaction(debt)
    debtor.add_transaction(debt)

    keyboard = [[]]

    update.effective_message.edit_text(text=lang.get_text("new_debt_resume",
                                                          amount=debt.amount,
                                                          comment=debt.comment,
                                                          lender=lender.full_name,
                                                          debtor=debtor.full_name,
                                                          title=group_manager.get_group_by_id(debt.group_id).title),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)

    user_data["editing"] = debt.group_id


def new_transaction_cancel(bot, update, user_data):
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    transaction_id = data.split("*")[1]
    group = group_manager.get_group_by_id(transaction_manager.get_transaction_by_id(transaction_id).group_id)
    transaction_manager.remove_transaction(transaction_id)

    update.effective_message.edit_text(lang.get_text("transaction_canceled", title=group.title),
                                       parse_mode=ParseMode.MARKDOWN)
    user_data["editing"] = group.id


# Inline shit
def valid_inline_query(bot, update, user_data):
    """DEPRECATED"""
    # Devuelve resultados a la query que se ha recibido, que tendrá un formato correcto "<cantidad> <comentario>"
    # DEPRECATED: Las funciones de inline_query han sido desactivadas en el bot.

    query = update.inline_query
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = query.query
    amount, comment = data.split()

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(lang.get_text("confirm"),
                                                               callback_data="new-purchase-%s-%s" % (amount, comment))],
                                         [InlineKeyboardButton(lang.get_text("cancel"),
                                                               callback_data="cancel_new_trancaction")]])
    purchase = InlineQueryResultArticle(
        id=0,
        title=lang.get_text("create_purchase"),
        description=lang.get_text("create_purchase_description"),
        reply_markup=reply_markup,
        input_message_content=InputTextMessageContent(lang.get_text("create_purchase_message",
                                                                    comment=comment,
                                                                    amount=amount),
                                                      parse_mode=ParseMode.MARKDOWN)
    )

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(lang.get_text("confirm"),
                                                               callback_data="new-trasnfer-%s-%s" % (amount, comment))],
                                         [InlineKeyboardButton(lang.get_text("cancel"),
                                                               callback_data="cancel_new_trancaction")]])

    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(lang.get_text("confirm"),
                                                               callback_data="new-debt-%s-%s" % (amount, comment))],
                                         [InlineKeyboardButton(lang.get_text("cancel"),
                                                               callback_data="cancel_new_trancaction")]])

    results = [purchase]
    query.answer(id=0, results=results, switch_pm_text=lang.get_text("word_help"), switch_pm_parameter="help")


def not_valid_inline_query(bot, update, user_data):
    """DEPRECATED"""
    # Contesta a una inline_query con formato incorrecto, sugeriendo cómo hacerlo.
    # DEPRECATED: Las funciones de inline_query han sido desactivadas en el bot.

    query = update.inline_query
    data = query.query
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(lang.get_text("word_help"),
                                                               url="t.me/%s?start=help" % const.aux.bot_username)]])

    if data != "":
        results = [InlineQueryResultArticle(0,
                                            lang.get_text("incorrect_format"),
                                            InputTextMessageContent(lang.get_text("incorrect_format_message"),
                                                                    parse_mode=ParseMode.MARKDOWN),
                                            description=lang.get_text("inline_empty_incorrect_format_description"),
                                            reply_markup=reply_markup)]

        query.answer(results=results,
                     switch_pm_text=lang.get_text("word_help"),
                     switch_pm_parameter="help")

    else:
        results = [InlineQueryResultArticle(0,
                                            lang.get_text("inline_empty"),
                                            InputTextMessageContent(
                                                lang.get_text("inline_empty_message"),
                                                parse_mode=ParseMode.MARKDOWN),
                                            description=lang.get_text("inline_empty_incorrect_format_description"),
                                            reply_markup=reply_markup)]

        query.answer(results=results,
                     switch_pm_text=lang.get_text("word_help"),
                     switch_pm_parameter="help")
