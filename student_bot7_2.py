async def generate_and_send_report(update_or_query, context, student_id, student_name, start_date, today):
    async with db_pool.acquire() as conn:
        detail_query = """
            SELECT 
                d.date_val AS log_date, 
                t.section, 
                t.title AS task_title,
                COALESCE(l.is_done, FALSE) AS is_done,
                COALESCE(l.reflection, '') AS reflection
            FROM routine_templates t
            CROSS JOIN (
                SELECT generate_series($2::date, $3::date, '1 day'::interval)::date AS date_val
            ) d
            LEFT JOIN student_daily_logs l 
                ON l.template_id = t.id 
                AND l.student_id = $1 
                AND l.log_date = d.date_val
            WHERE t.status = 'active' AND t.batch_id = $4
            ORDER BY d.date_val DESC, t.section ASC, t.task_order ASC;
        """
        # 🟢 $4 နေရာတွင် BATCH_ID ကို ထည့်သွင်းပေးခြင်း
        rows = await conn.fetch(detail_query, student_id, start_date, today, BATCH_ID)

    if not rows:
        msg = f"📌 {student_name} အတွက် ပြီးခဲ့သည့် ၇ ရက်အတွင်း ဒေတာ မရှိသေးပါ။"
        if isinstance(update_or_query, Update) and update_or_query.callback_query:
            await update_or_query.callback_query.edit_message_text(msg)
        elif hasattr(update_or_query, "edit_message_text"):
            await update_or_query.edit_message_text(msg)
        else:
            await update_or_query.message.reply_text(msg)
        return

    report_text = f"📊 {student_name} ၏ (၇) ရက်တာ အစီရင်ခံစာ (Batch TharThar)\n\n"
    done_count = sum(1 for r in rows if r["is_done"])
    total_count = len(rows)
    report_text += f"✅ ပြီးစီးမှု: {done_count}/{total_count} Tasks\n"
    report_text += "-----------------------------------\n"
    
    for r in rows[:15]: 
        status_icon = "✅" if r["is_done"] else "❌"
        report_text += f"{r['log_date']} | {r['section']} | {r['task_title']} - {status_icon}\n"

    try:
        if isinstance(update_or_query, Update) and update_or_query.callback_query:
            await update_or_query.callback_query.edit_message_text(report_text)
        elif hasattr(update_or_query, "edit_message_text"):
            await update_or_query.edit_message_text(report_text)
        else:
            message = update_or_query.message or update_or_query.effective_message
            await message.reply_text(report_text)
    except Exception as e:
        print(f"❌ Send Report Error: {e}")
