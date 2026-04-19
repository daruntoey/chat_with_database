import streamlit as st
import pandas as pd
import sqlite3
from google import genai
from google.genai import types
import json

# 1. API Setup
gemini_api_key = st.secrets["gemini_api_key"]
gmn_client = genai.Client(api_key=gemini_api_key)

db_name = 'test_database.db'
data_table = 'transactions'
data_dict_text = """
- trx_date: วันที่ทำธุรกรรม
- trx_no: หมายเลขธุรกรรม
- member_code: รหัสสมาชิกของลูกค้า
- branch_code: รหัสสาขา
- branch_region: ภูมิภาคที่สาขาตั้งอยู่
- branch_province: จังหวัดที่สาขาตั้งอยู่
- product_code: รหัสสินค้า
- product_category: หมวดหมู่หลักของสินค้า
- product_group: กลุ่มของสินค้า
- product_type: ประเภทของสินค้า
- order_qty: จำนวนชิ้น/หน่วย ที่ลูกค้าสั่งซื้อ
- unit_price: ราคาขายของสินค้าต่อหน่วย
- cost: ต้นทุนของสินค้าต่อหน่วย
- item_discount: ส่วนลดเฉพาะรายการสินค้านั้นๆ
- customer_discount: ส่วนลดจากสิทธิของลูกค้า
- net_amount: ยอดขายสุทธิของรายการนั้น
- cost_amount: ต้นทุนรวมของรายการนั้น
"""

# 2. HELPER FUNCTIONS
def query_to_dataframe(sql_query, database_name):
    try:
        connection = sqlite3.connect(database_name)
        result_df = pd.read_sql_query(sql_query, connection)
        connection.close()
        return result_df
    except Exception as e:
        return f"Database Error: {e}"

def generate_gemini_answer(prompt, is_json=False):
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if is_json else "text/plain" 
        )
        response = gmn_client.models.generate_content(
            model='gemini-2.0-flash-lite', # Updated to a valid model name
            contents=prompt,
            config=config)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# 3. PROMPT TEMPLATES (Ensure placeholders match .format() keys)
script_prompt = """
Generate an SQL query based on this:
Question: {question}
Table: {table_name}
Data Dictionary: {data_dict}
Return ONLY JSON: {{"script": "SELECT ..."}}
"""

answer_prompt = """
Based on the data below, answer the user's question.
Question: {question}
Data: {raw_data}
"""

# 4. CORE LOGIC
def generate_summary_answer(user_question):
    # Step A: Generate SQL
    script_prompt_input = script_prompt.format(
        question=user_question,
        table_name=data_table,
        data_dict=data_dict_text
    )
    
    # FIXED: Use generate_gemini_answer here
    sql_json_text = generate_gemini_answer(script_prompt_input, is_json=True)
    
    try:
        sql_script = json.loads(sql_json_text)['script']
    except Exception as e:
        return f"ขออภัย ไม่สามารถสร้าง SQL ได้: {e}"

    # Step B: Run Query
    df_result = query_to_dataframe(sql_script, db_name)
    if isinstance(df_result, str):
        return df_result

    # Step C: Generate Final Answer
    answer_prompt_input = answer_prompt.format(
        question=user_question,
        raw_data=df_result.to_string()
    )
    
    # FIXED: Use generate_gemini_answer here
    return generate_gemini_answer(answer_prompt_input, is_json=False)

# 5. USER INTERFACE
st.title('Gemini Chat with Database')

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("พิมพ์คำถามที่นี่..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner('กำลังหาคำตอบ...'):
            response = generate_summary_answer(prompt)
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
