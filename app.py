from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = 'plant_cbt_secret_key_2026_fixed'

def get_db():
  base_dir = os.path.dirname(os.path.abspath(__file__))
  db_file = os.path.join(base_dir, 'plants_db.csv')
  if not os.path.exists(db_file):
    return pd.DataFrame()
  try:
    df = pd.read_csv(db_file, encoding='utf-8-sig')
  except:
    df = pd.read_csv(db_file, encoding='utf-8')
  df.columns = df.columns.str.strip().str.strip("'").str.strip('"')
  return df.fillna('')

def parse_images(img_str):
    if not img_str:
        return []
    return [img.strip() for img in str(img_str).split(',') if img.strip()]

@app.route('/')
def start():
    df = get_db()
    total_species = len(df)
    return render_template('start.html', total_species=total_species)

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    df = get_db()
    num_q = int(request.form.get('num_questions', 20))
    
    sampled_df = df.sample(n=min(num_q, len(df)))
    session['quiz_codes'] = sampled_df['code'].tolist()
    session['total_q'] = len(sampled_df)
    session['curr'] = 0
    session['answers'] = {}
    return redirect(url_for('quiz'))

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    quiz_codes = session.get('quiz_codes', [])
    curr = session.get('curr', 0)
    answers = session.get('answers', {})
    total_q = session.get('total_q', 0)

    if not quiz_codes or curr >= len(quiz_codes):
        return redirect(url_for('start'))

    df = get_db()
    current_code = quiz_codes[curr]
    row = df[df['code'] == current_code].to_dict(orient='records')
    
    if not row:
        return redirect(url_for('start'))
    
    item = row[0]
    item['img_list'] = parse_images(item.get('images', ''))

    if request.method == 'POST':
        # 속(genus) 제외, 3개 항목만 수집
        answers[str(curr)] = {
            'family': request.form.get('family', '').strip(),
            'species': request.form.get('species', '').strip(),
            'endangered': request.form.get('endangered', '').strip()
        }
        session['answers'] = answers

        action = request.form.get('action')
        if action == 'prev' and curr > 0:
            session['curr'] = curr - 1
        elif action == 'next' and curr < len(quiz_codes) - 1:
            session['curr'] = curr + 1
        elif action == 'submit':
            return redirect(url_for('result'))
        
        return redirect(url_for('quiz'))

    return render_template(
        'quiz.html',
        item=item,
        idx=curr,
        total=total_q,
        saved=answers.get(str(curr), {})
    )

@app.route('/result')
def result():
    quiz_codes = session.get('quiz_codes', [])
    answers = session.get('answers', {})
    total_q = session.get('total_q', 0)

    if not quiz_codes:
        return redirect(url_for('start'))

    df = get_db()
    score_per_item = 100.0 / (total_q * 3) # 총 3개 항목(과, 종명, 멸종위기종) 기준 배점
    total_score = 0.0
    results = []

    for idx, code in enumerate(quiz_codes):
        row = df[df['code'] == code].to_dict(orient='records')
        if not row:
            continue
        item = row[0]
        item['img_list'] = parse_images(item.get('images', ''))
        
        user_ans = answers.get(str(idx), {})
        
        def clean(val):
            return str(val).replace(" ", "").lower()

        check = {
            'family': clean(user_ans.get('family', '')) == clean(item.get('family', '')),
            'species': clean(user_ans.get('species', '')) == clean(item.get('species', '')),
            'endangered': clean(user_ans.get('endangered', '')) == clean(item.get('endangered', '')),
        }
        
        correct_count = sum(check.values())
        item_score = correct_count * score_per_item
        total_score += item_score

        results.append({
            'num': idx + 1,
            'item': item,
            'user_ans': user_ans,
            'check': check,
            'item_score': round(item_score, 2)
        })

    return render_template(
        'result.html',
        results=results,
        total_score=round(total_score, 2),
        total_q=total_q,
        score_per_item=score_per_item
    )

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    df = get_db()
    results = []

    if query:
        filtered = df[
            df['species'].str.contains(query, case=False, na=False) |
            df['family'].str.contains(query, case=False, na=False)
        ]
        for _, row in filtered.iterrows():
            item = row.to_dict()
            item['img_list'] = parse_images(item.get('images', ''))
            results.append(item)

    return render_template('search.html', query=query, results=results)

@app.route('/custom', methods=['GET', 'POST'])
def custom_quiz():
    df = get_db()
    if request.method == 'POST':
        selected_codes = request.form.getlist('selected_codes')
        if not selected_codes:
            return redirect(url_for('custom_quiz'))
        
        session['quiz_codes'] = selected_codes
        session['total_q'] = len(selected_codes)
        session['curr'] = 0
        session['answers'] = {}
        return redirect(url_for('quiz'))

    species_list = []
    for _, row in df.iterrows():
        species_list.append({
            'code': row['code'],
            'species': row['species'],
            'family': row['family']
        })
    return render_template('custom.html', species_list=species_list)

if __name__ == '__main__':
    app.run(debug=True)