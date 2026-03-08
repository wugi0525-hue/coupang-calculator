# python -m pip install python-telegram-bot python-dotenv
import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv

import sys
# 한글 인코딩 방지
sys.stdout.reconfigure(encoding='utf-8')

# 포스팅 메인 루프 가져오기
from coupang_auto_poster import run_auto_poster

load_dotenv()

# Replace with your Telegram Bot Token
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") 
# 만약 .env에 봇 토큰이 없다면 임시로 RPA 봇 토큰이나 새로 발급받은 토큰을 여기에 하드코딩 (보안 주의)
if not BOT_TOKEN:
    # RPA 봇이랑 같은 봇을 쓰시려면 그 토큰을 넣으셔도 됩니다.
    BOT_TOKEN = "8739013685:AAFli3DfBh_wmK21brh6kKe93yqskuRhS9s" 

AUTHORIZED_USER_ID = 7222279833 # 사용자님의 고유 텔레그램 ID (보안용)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_USER_ID:
        await update.message.reply_text(f"인가되지 않은 사용자입니다. (ID: {user_id})")
        return ConversationHandler.END

    keyboard = [["🚀 자동 포스팅 공장 가동 🚀"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_text(
        "안녕하세요 대표님! 🤖 쿠팡 랭킹 자동 포스팅 봇입니다.\n\n"
        "회사에서 깃허브에 raw_data를 업로드 하셨나요?\n"
        "업로드를 마치셨다면 아래 버튼을 눌러 작업을 지시해 주세요.",
        reply_markup=reply_markup
    )
    return 1 # State: WAIT_FOR_COMMAND

async def run_posting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id != AUTHORIZED_USER_ID:
        return ConversationHandler.END

    text = update.message.text
    if "포스팅 공장 가동" in text:
        # 메시지 창을 하나 띄어두고, 진행 상황(콜백)이 올 때마다 내용을 갱신
        msg = await update.message.reply_text("🔄 시스템 부팅 중... 쿠팡 로직을 초기화합니다.\n(약 10초~수 분 소요)", reply_markup=ReplyKeyboardRemove())
        
        # 콜백용 상태 텍스트 누적
        status_lines = []

        async def status_callback(report_text):
            # 텔레그램은 메시지 수정이 빈번하면 타임아웃이 날 수 있으므로, 
            # 중요 메시지만 출력하도록 적절히 누적해서 보여줍니다.
            print(f"[Bot] {report_text}")
            status_lines.append(report_text)
            
            # 너무 길어지면 뒤에서 5줄만 유지 
            if len(status_lines) > 7:
                display_lines = status_lines[-7:]
            else:
                display_lines = status_lines
                
            display_text = "💡 [자동화 공장 가동 현황]\n\n" + "\n".join(display_lines)
            try:
                # 텔레그램 API 특성 상 완전히 동일한 텍스트로 수정하려 하면 예외가 발생하므로 패스
                await msg.edit_text(display_text)
            except Exception:
                pass

        try:
            # 쿠팡 오토 포스터 실행 (비동기로 대기)
            # 실행 직전에 크롬창이 반드시 띄워져 있어야 합니다. (launch_chrome.py 선행 실행 필요)
            success = await run_auto_poster(status_callback=status_callback)
            
            if success:
                await update.message.reply_text("🎉 모든 상품 네이버 블로그 포스팅 발행이 완료되었습니다!")
            else:
                await update.message.reply_text("❌ 스크립트 실행 중 문제가 발생했습니다. (크롬 구동 상태나 JSON 파일을 확인하세요)")
                
        except Exception as e:
            await update.message.reply_text(f"❌ 치명적 오류 발생: {str(e)}")
            
        return ConversationHandler.END
    else:
        await update.message.reply_text("알 수 없는 명령입니다.")
        return 1

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("명령이 취소되었습니다.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main() -> None:
    print("🤖 Telegram Bot Started... (Coupang Auto Poster Edition)")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, run_posting)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
