# coding=utf-8
# Archivo: handlers
# Descripción: Aquí se declararán los handlers a las distintas llamadas de la API.

import re
import const
import utils
from math import ceil
from lang import get_lang

from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle,\
    InputTextMessageContent, ForceReply

from group_manager import group_manager
from user_manager import user_manager
from transaction_manager import transaction_manager

re_amount_comment = re.compile(const.RE_AMOUNT_COMMENT_PATTERN)


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


# Bot Commands
def add(bot, update, args, chat_data, user_data):
    # Pide más datos o crea una transacción con los datos proporcionados.
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)

    if args:
        if re_amount_comment.match(utils.join_unicode_list(args, " ")):
            select_transaction_type(bot, update, user_data)

            return
    update.effective_message.reply_text(lang.get_text("add_message"),
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=ForceReply(selective=True))


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
            group.add_user(user)

    if new_group:
        keyboard = [[InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")],
                    [InlineKeyboardButton(lang.get_text("create_purchase"), callback_data="new_pur")]]
        # keyboard = [[InlineKeyboardButton(lang.get_text("presentarse"), callback_data="hi_group")]]

        update.effective_message.reply_text(lang.get_text("new_group"),
                                            reply_markup=InlineKeyboardMarkup(keyboard),
                                            reply=False,
                                            parse_mode=ParseMode.MARKDOWN)


def select_transaction_type(bot, update, user_data):
    # Este método se ejecutará cuando el bot reciba un mensaje con el formato "<cantidad> <comentario>", que
    # deberia ser una contestación al mensaje de new_members, cuando reciba el comando /add.

    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    if "/add" in update.effective_message.text:
        i = 1
    else:
        i = 0
    amount = update.effective_message.text.split()[i]
    comment = utils.join_unicode_list(update.effective_message.text.split()[i + 1:], space=" ") # TODO: hacer esto con un .replace(), que será notablemente más eficiente que paretir en cachos el text dos veces.
    del i

    keyboard = [[InlineKeyboardButton(lang.get_text("purchase"), callback_data="n_pur*%s*%s"[:64] % (amount,
                                                                                                            comment)),
                 InlineKeyboardButton(lang.get_text("transfer"), callback_data="n_tra*%s*%s"[:64] % (amount,
                                                                                                            comment)),
                 InlineKeyboardButton(lang.get_text("debt"), callback_data="n_de*%s*%s"[:64] % (amount, comment))]]

    update.effective_message.reply_text(lang.get_text("select_transaction_type_message",
                                                      amount=amount,
                                                      comment=comment),
                                        parse_mode=ParseMode.MARKDOWN,
                                        reply_markup=InlineKeyboardMarkup(keyboard))


def message(bot, update, chat_data):
    # Se ejecuta cuando recibe un mensaje cualquiera que no haya pasado los filtros, sólo para debugging.

    print update.effective_message.text


# Inline buttons
def none(bot, update):
    # Para los botones que no debería hacer nada o simplemente mostrar un texto en pantalla.

    text = update.callback_query.data.split("*")[1]

    update.callback_query.answer(text)


def hi_button(bot, update, chat_data, user_data):
    # Para el botón en el que los usuarios se presentan al bot para ser añadidos al grupo.

    group = group_manager.get_group(update.effective_chat, chat_data)
    user = user_manager.get_user(update.effective_user, user_data)
    group.add_user(update.effective_user)
    lang = get_lang(user.language_code)

    update.callback_query.answer(lang.get_text("hi",
                                               user_full_name_simple=user.full_name_simple,
                                               group_name=update.effective_chat.title))


def new_purchase(bot, update, chat_data, user_data):
    # Para el botón de añadir una compra, mostrado en el mensaje de saludo (new_members) y en otros mensajes.

    group = group_manager.get_group(update.effective_chat, chat_data)
    user = user_manager.get_user(update.effective_user, user_data)
    lang = get_lang(user.language_code)
    data = update.callback_query.data
    amount, comment = data.split("*")[1:]

    purchase = transaction_manager.add_transaction(transaction_type="purchase",
                                                   amount=amount,
                                                   comment=comment,
                                                   buyer=user.id,
                                                   participants=group.user_list,
                                                   group_id=group.id)

    group.add_user(user)

    # Mensaje al grupo
    keyboard = [[InlineKeyboardButton(lang.get_text("goto_pm"), url="t.me/%s" % const.aux.bot_username)]]

    update.effective_message.edit_text(lang.get_text("goto_pm_message", bot_username=const.aux.bot_username),
                                       parse_mode=ParseMode.MARKDOWN,
                                       reply_markup=InlineKeyboardMarkup(keyboard))

    # Mensaje PM
    keyboard = []
    for participant in group.user_list[:5]:
        text = "⚪️ " if participant.id != purchase.buyer else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + participant.full_name_simple,
                                              callback_data="n_pur_bu_sel*%d*0*%s" % (participant.id,
                                                                                        purchase.id))])
    if len(group.user_list) > 5:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_pur_bu_p*0*%s" % purchase.id),
                         InlineKeyboardButton("⬅️", callback_data="n_pur_bu_p*0*%s" % purchase.id),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=0)),
                         InlineKeyboardButton("➡️", callback_data="n_pur_bu_p*1*%s" % purchase.id),
                         InlineKeyboardButton("⏩", callback_data="n_pur_bu_p*%d*%s" %
                                                                 (int(ceil(len(group.user_list) / 5.0)), purchase.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_pur_pa_p*0*%s" % purchase.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="cancel*n_pur_bu_p*0*%s" % purchase.id)])

    bot.send_message(chat_id=user.id,
                     text=lang.get_text("select_buyer", buyer=user_manager.get_user_by_id(purchase.buyer).full_name),
                     reply_markup=InlineKeyboardMarkup(keyboard),
                     parse_mode=ParseMode.MARKDOWN)


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
        purchase.set_buyer(buyer_id)
    else:
        print "wtf es %s" % cmd
        return

    group = group_manager.get_group_by_id(purchase.group_id)
    last_page = int(ceil(len(group.user_list) / 5.0)) - 1
    next_page = last_page if page >= last_page else page + 1

    keyboard = []
    for participant in group.user_list[5 * page:5 + 5 * page]:
        text = "⚪️ " if participant.id != purchase.buyer else "🔘 ️"
        keyboard.append([InlineKeyboardButton(text + participant.full_name_simple,
                                              callback_data="n_pur_bu_sel*%d*%d*%s" % (participant.id,
                                                                                       page,
                                                                                       purchase.id))])
    if len(group.user_list) > 5:
        keyboard.append([InlineKeyboardButton("⏪", callback_data="n_pur_bu_p*0*%s" % purchase.id),
                         InlineKeyboardButton("⬅️", callback_data="n_pur_bu_p*%d*%s" % (0 if page <= 0 else page - 1,
                                                                                        purchase.id)),
                         InlineKeyboardButton("0️⃣", callback_data="none*%s" % lang.get_text("page", page=page)),
                         InlineKeyboardButton("➡️", callback_data="n_pur_bu_p*%d*%s" % (next_page, purchase.id)),
                         InlineKeyboardButton("⏩", callback_data="n_pur_bu_p*%d*%s" % (last_page, purchase.id))])

    keyboard.append([InlineKeyboardButton(lang.get_text("confirm"),
                                          callback_data="n_pur_pa_p*0*%s" % purchase.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="cancel*n_pur_bu_p*0*%s" % purchase.id)])

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
        purchase.add_remove_participant(participant_id)
    else:
        print "wtf es %s" % cmd
        return

    group = group_manager.get_group_by_id(purchase.group_id)
    last_page = int(ceil(len(group.user_list) / 5.0)) - 1
    next_page = last_page if page >= last_page else page + 1

    keyboard = []
    for participant in group.user_list[5 * page:5 + 5 * page]:
        text = "❎" if participant.id != purchase.buyer else "☑️"
        keyboard.append([InlineKeyboardButton(text + participant.full_name_simple,
                                              callback_data="n_pur_pa_sel*%d*%d*%s" % (participant.id,
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
                                          callback_data="n_pur_pa_p*0*%s" % purchase.id),
                     InlineKeyboardButton(lang.get_text("cancel"),
                                          callback_data="cancel*n_pur_pa_p*0*%s" % purchase.id)])

    participant_name_list = [user_manager.get_user_by_id(x).full_name for x in purchase.participants]

    update.effective_message.edit_text(text=lang.get_text("select_participant",
                                                          buyer=user_manager.get_user_by_id(purchase.buyer).full_name,
                                                          participants=lang.enum(participant_name_list)),
                                       reply_markup=InlineKeyboardMarkup(keyboard),
                                       parse_mode=ParseMode.MARKDOWN,
                                       disable_web_page_preview=True)


# Inline shit
def valid_inline_query(bot, update, user_data):
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
