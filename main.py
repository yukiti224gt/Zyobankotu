# インポートするライブラリ
from flask import Flask, request, abort
import psycopg2
from psycopg2.extras import DictCursor
import re
import json
import sys
import os
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    FollowEvent, MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ButtonsTemplate, PostbackTemplateAction, MessageTemplateAction, URITemplateAction, PostbackEvent
)

# 軽量なウェブアプリケーションフレームワーク:Flask
app = Flask(__name__)  # 環境変数からLINE Access Tokenを設定
# 環境変数からLINE Channel Secretを設定
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

DATABASE_URL = os.environ.get('POSTGRESQL_DB_URL')


@ app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(FollowEvent)
def on_follow(event):
    reply_token = event.reply_token
    user_id = event.source.user_id
    profiles = line_bot_api.get_profile(user_id=user_id)
    display_name = profiles.display_name

    # DBへの保存
    try:
        conn = psycopg2.connect(DATABASE_URL)
        c = conn.cursor()
        sql = "SELECT name FROM user_data WHERE id = '"+user_id+"';"
        c.execute(sql)
        ret = c.fetchall()
        if len(ret) == 0:
            sql = "INSERT INTO user_data (id, name) VALUES ('" + \
                user_id+"', '"+str(display_name)+"');"
        elif len(ret) == 1:
            sql = "UPDATE user_data SET name = " + \
                str(display_name) + "WHERE id = '"+user_id+"';"
        c.execute(sql)
        conn.commit()
    finally:
        conn.close()
        c.close()


@handler.add(PostbackEvent)
@ handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    m = re.match(r'^([01][0-9]|2[0-3]):[0-5][0-9]$', event.message.text)
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    if m != None:
        sql = "SELECT departure_time FROM  time_record WHERE departure_time > '" + \
            m.group(0)+"' limit 5;"
        c.execute(sql)
        ret = c.fetchall()

        line_bot_api.reply_message(
            event.reply_token,
            messages=TemplateSendMessage(
                alt_text="時刻検索結果",
                template=ButtonsTemplate(
                    text="バス時刻表検索",
                    actions=[
                        PostbackTemplateAction(
                            label=ret[0][0].strftime(
                                "%H:%M") + "発 "
                        ),
                        PostbackTemplateAction(
                            label=ret[1][0].strftime(
                                "%H:%M") + "発 "
                        ),

                        PostbackTemplateAction(
                            label=ret[2][0].strftime(
                                "%H:%M") + "発 "
                        ),
                        PostbackTemplateAction(
                            label=ret[3][0].strftime(
                                "%H:%M") + "発 "
                        )
                    ]
                )
            )
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="出発したい時間を入力してください！\nその後の直近５件の時刻を教えます。\n(例)09:00, 12:00, 15:30")
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)
