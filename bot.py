# coding=utf-8
# Archivo: bot
# Descripción: el bot se ejecutará desde este archivo. Aquí se asignarán las funciones handler del archivo handlers.py
# a una llamada de la API.

import logging
import handlers as h
from telegram.ext import Updater, InlineQueryHandler, ChosenInlineResultHandler, CallbackQueryHandler,\
    CommandHandler, MessageHandler, Filters, PreCheckoutQueryHandler, BaseFilter, RegexHandler
from bot_tokens import BOT_TOKEN
import const

# Console logger
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def stop_bot(updater):
    # Función que da la señal al updater para que deje de hacer pooling
    logger.info("Apagando bot...")
    h.auto_save()
    updater.stop()
    logger.info("Bot apagado")


def main():
    updater = Updater(BOT_TOKEN)
    a = updater.dispatcher.add_handler

    get_me_bot = updater.bot.get_me()
    const.aux.bot_id = get_me_bot.id
    const.aux.bot_username = get_me_bot.username
    const.aux.bor = updater.bot
    del get_me_bot

    # Asignación de handlers
    # COMANDOS
    a(CommandHandler('start', h.start, pass_args=True))
    a(CommandHandler('help', h.help))
    a(CommandHandler('more', h.more))
    a(CommandHandler('donate', h.donate))
    a(CommandHandler('add', h.add, filters=Filters.group, pass_chat_data=True, pass_user_data=True, pass_args=True))
    a(CommandHandler('split', h.split, filters=Filters.group, pass_chat_data=True, pass_user_data=True))
    a(CommandHandler('history', h.history_group, filters=Filters.group, pass_user_data=True, pass_chat_data=True))
    a(CommandHandler('introduce', h.introduce, filters=Filters.group, pass_chat_data=True, pass_user_data=True))
    a(CommandHandler('save', h.force_save))
    # MENSAJES
    a(MessageHandler(Filters.status_update.new_chat_members, h.new_members, pass_chat_data=True))
    a(MessageHandler(Filters.status_update.left_chat_member, h.left_chat_members, pass_chat_data=True))
    a(MessageHandler(Filters.regex(pattern=const.RE_AMOUNT_COMMENT_PATTERN) & Filters.group,
                     callback=h.select_transaction_type_group,
                     pass_user_data=True))
    a(MessageHandler(Filters.regex(pattern=const.RE_AMOUNT_COMMENT_PATTERN) & Filters.private,
                     callback=h.select_transaction_type_pm,
                     pass_user_data=True))
    a(MessageHandler(Filters.text, h.message, pass_chat_data=True))
    # BOTONES
    a(CallbackQueryHandler(h.hi_button, pattern=r"hi_group$", pass_chat_data=True, pass_user_data=True))
    a(CallbackQueryHandler(h.new_purchase_buyer, pattern="n_pur_bu_(sel|p)", pass_user_data=True))
    a(CallbackQueryHandler(h.new_purchase_participants, pattern="n_pur_pa_(sel|p)", pass_user_data=True))
    a(CallbackQueryHandler(h.new_purchase_resume, pattern="n_pur_res", pass_user_data=True))
    a(CallbackQueryHandler(h.new_purchase, pattern="n_pur", pass_user_data=True, pass_chat_data=True))
    a(CallbackQueryHandler(h.new_transfer_payer, pattern="n_tra_pa_(sel|p)", pass_user_data=True))
    a(CallbackQueryHandler(h.new_transfer_receiver, pattern="n_tra_re_(sel|p)", pass_user_data=True))
    a(CallbackQueryHandler(h.new_transfer_resume, pattern="n_tra_res", pass_user_data=True))
    a(CallbackQueryHandler(h.new_transfer, pattern="n_tra", pass_user_data=True, pass_chat_data=True))
    a(CallbackQueryHandler(h.new_debt_lender, pattern="n_dbt_le_(sel|p)", pass_user_data=True))
    a(CallbackQueryHandler(h.new_debt_debtor, pattern="n_dbt_de_(sel|p)", pass_user_data=True))
    a(CallbackQueryHandler(h.new_debt_resume, pattern="n_dbt_res", pass_user_data=True))
    a(CallbackQueryHandler(h.new_debt, pattern="n_dbt", pass_user_data=True, pass_chat_data=True))
    a(CallbackQueryHandler(h.new_transaction_cancel, pattern="n_trc_c", pass_user_data=True))
    a(CallbackQueryHandler(h.history_group, pattern="hi", pass_user_data=True, pass_chat_data=True))
    a(CallbackQueryHandler(h.transaction_info, pattern=r"tr\*", pass_chat_data=True, pass_user_data=True))
    a(CallbackQueryHandler(h.delete_transaction, pattern=r"del_tr\*", pass_user_data=True, pass_chat_data=True))
    a(CallbackQueryHandler(h.none, pattern=r"none"))
    # INLINE SHIT
    a(InlineQueryHandler(h.valid_inline_query, pass_user_data=True, pattern=r"\d+((\.|,)\d+)* (\w *)+"))
    a(InlineQueryHandler(h.not_valid_inline_query, pass_user_data=True))

    updater.dispatcher.add_error_handler(h.error_handler)

    updater.job_queue.run_repeating(h.auto_save, 3600)

    # Iniciar bot, comenzar a hacer pooling
    updater.start_polling()

    # CONSOLA
    while True:
        inp = input("")
        if inp:
            input_c = inp.split()[0]
            args = inp.split()[1:]
            strig = ""
            for e in args:
                strig = strig + " " + e

            if input_c == "stop":
                stop_bot(updater)
                break

            else:
                print("Comando desconocido")


if __name__ == '__main__':
    main()
