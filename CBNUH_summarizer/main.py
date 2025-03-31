from flask import Flask, request, render_template, send_file, session
import pandas as pd
from io import BytesIO
from preprocess_df import ExcelProcessor  # preprocess_df.py에 정의된 클래스 가져오기
from transformers import pipeline
from collections import defaultdict
import base64
import copy, os
from pyngrok import conf, ngrok

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션을 사용하기 위한 비밀 키 설정


# 요약 모델 로드
summarizer = pipeline("summarization", model='seop/CBNUH-summarizer')

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html', file_url=None, error="No file part in the request")
        
        file = request.files['file']
        if file.filename == '':
            return render_template('index.html', file_url=None, error="No file selected")
        
        processor = ExcelProcessor(summarizer)
        data_file = pd.read_excel(file)
        if len(data_file.columns)==12:
            df = processor.process_file(data_file)
        else:
            df = data_file
        df2=copy.deepcopy(df)
        # 통계 정보 생성
        statistics = process_statistics(df2)
        # 처리된 파일을 메모리에 저장
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        
        # 처리된 파일을 base64로 인코딩
        processed_file_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
        
        # 원본 파일 이름을 세션에 저장
        session['original_filename'] = file.filename

        return render_template('index.html', statistics=statistics, processed_file=processed_file_base64)

    return render_template('index.html', file_url=None)

@app.route('/download', methods=['POST'])
def download_file():
    processed_file_base64 = request.form['processed_file']
    processed_file = base64.b64decode(processed_file_base64)
    output = BytesIO(processed_file)
    output.seek(0)
    
    # 원본 파일 이름을 세션에서 가져와서 새로운 파일 이름 생성
    original_filename = session.get('original_filename', 'processed_output')
    output_filename = f"{original_filename.rsplit('.', 1)[0]}_output.xlsx"
    
    return send_file(output, download_name=output_filename, as_attachment=True)

@app.route('/sample', methods=['GET', 'POST'])
def home_or_summarize():
    if request.method == 'GET':
        return render_template('index_sample.html', file_url=None, error="No file part in the request")
    
    if request.method == 'POST':
        input_text = request.form.get('input_text')
        if not input_text:
            return render_template('index_sample.html', file_url=None, error="No file part in the request")
        
        # 요약 수행
        summary = summarizer(input_text, max_new_tokens=2000)[0]['summary_text']
        return render_template('index_sample.html', file_url=None, summary=summary)
    return render_template('index_sample.html')

def process_statistics(df):
    df['채혈일'] = pd.to_datetime(df['채혈일'])
    df['YearMonth'] = df['채혈일'].dt.to_period('M')

    grouped = df.groupby(['YearMonth', '동정결과']).size().reset_index(name='Frequency')
    top_results = grouped.groupby('YearMonth').apply(lambda x: x.nlargest(5, 'Frequency')).reset_index(drop=True)

    antibiotics = ['OX', 'OX.1', 'FOXS', 'VA', 'VRS', 'ESBL', 'IPM', 'CL', 'AMC', 'ATM', 'CZ', 'FEP', 'CTX', 'CTX.1', 'FOX', 
                   'MEM', 'PIP', 'TZP', 'TIC', 'TIM', 'ISP', 'MI', 'NET', 'TOB', 'AM', 'AM.1', 'CIP', 'GM', 'SXT', 'P-G', 
                   'CC', 'E', 'LNZ', 'MXF', 'NIT', 'NOR', 'QDA', 'TE', 'FA', 'HAB', 'RIF', 'SAM', 'HLG', 'HLK', 'HLS', 'CRO', 
                   'CF', 'C', 'ERT', 'TIG']

    result = defaultdict(list)

    for _, row in top_results.iterrows():
        yearmonth = str(row['YearMonth'])
        result_type = row['동정결과']
        frequency = row['Frequency']

        filtered = df[(df['YearMonth'] == row['YearMonth']) & (df['동정결과'] == row['동정결과'])]
        total_count = len(filtered)

        antibiotic_stats = {}
        for ab in antibiotics:
            if ab in filtered.columns:
                s_count = (filtered[ab] == 'S').sum()
                antibiotic_stats[ab] = s_count / total_count

        sorted_ab = sorted(antibiotic_stats.items(), key=lambda x: x[1], reverse=True)[:5]
        result[yearmonth].append({
            'result_type': result_type,
            'frequency': frequency,
            'antibiotics': dict(sorted_ab)
        })

    return result

if __name__ == '__main__':

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        http_tunnel = ngrok.connect(5555)
        print("Public URL:", http_tunnel.public_url)

        tunnels = ngrok.get_tunnels()
        for kk in tunnels:
            print(kk)

    app.run(host='0.0.0.0', port=5555, debug=True)