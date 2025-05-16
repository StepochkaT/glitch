import json
import os
from calendar import monthrange, isleap
from datetime import datetime, date
import math
from PIL import Image
from dateutil.relativedelta import relativedelta

from flask import Flask, render_template, redirect, request, abort, jsonify, flash, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_apscheduler import APScheduler
from werkzeug.utils import secure_filename

from currency_updater import update_currency_data, load_data

from data.category import Category
from forms.budget_form import BudgetForm
from forms.cat_form import CategoryForm
from forms.credit_calc import CreditCalculatorForm
from forms.deposit_calc import DepositCalculatorForm
from forms.image import UploadImageForm
from forms.period import PeriodForm
from forms.save_calc import SavingsCalculatorForm
from forms.user import RegisterForm, LoginForm, NameChangeForm, PasswordStepOneForm, PasswordStepTwoForm
from forms.operation import OperationForm
from data.users import User
from data.operations import Operation
from data.budget import Budget
from data import db_session

from collections import defaultdict

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'super_secret_key'


class Config:
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

scheduler.add_job(
    id='update_currency_data',
    func=update_currency_data,
    trigger='interval',
    hours=2
)



@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


def main():
    db_session.global_init("db/database2.db")
    app.run()


@app.route("/")
def index():
    if current_user.is_authenticated:
        now = datetime.now()
        current_month = now.strftime("%B %Y")
        session = db_session.create_session()
        budget_set = session.query(Budget).filter(
            Budget.user_id == current_user.id,
            Budget.year == now.year,
            Budget.month == now.month
        ).first()

        operations_this_month = list(filter(
            lambda op: op.date.month == now.month and op.date.year == now.year,
            current_user.operations
        ))

        if now.month == 1:
            prev_month = 12
            prev_year = now.year - 1
        else:
            prev_month = now.month - 1
            prev_year = now.year

        operations_last_month = list(filter(
            lambda op: op.date.month == prev_month and op.date.year == prev_year,
            current_user.operations
        ))

        income = sum(op.amount for op in operations_this_month if op.type == "income")
        expense = sum(op.amount for op in operations_this_month if op.type == "expense")
        balance = income - expense

        income_last = sum(op.amount for op in operations_last_month if op.type == "income")
        expense_last = sum(op.amount for op in operations_last_month if op.type == "expense")

        def calc_change(current, previous):
            if previous == 0:
                return None
            return round((current - previous) / previous * 100, 1)

        income_change = calc_change(income, income_last)
        expense_change = calc_change(expense, expense_last)

        return render_template(
            "dashboard.html",
            authenticated=True,
            income=income,
            expense=expense,
            balance=balance,
            income_change=income_change,
            expense_change=expense_change,
            current_month=current_month,
            budget_missing=(budget_set is None)
        )
    else:
        return render_template("dashboard.html", authenticated=False)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            username=form.username.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        print('smth')
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/add_operation', methods=['GET', 'POST'])
@login_required
def add_operation():
    form = OperationForm()

    db_sess = db_session.create_session()
    categories = db_sess.query(Category).filter(
        (Category.user_id == None) | (Category.user_id == current_user.id)
    ).all()

    form.category.choices = [(cat.id, cat.name) for cat in categories]

    if form.validate_on_submit():
        description = form.description.data.strip()
        if not description:
            description = "Без описания"

        operation = Operation(
            date=form.date.data,
            amount=form.amount.data,
            category_id=form.category.data,
            type=form.type.data,
            description=description,
            user_id=current_user.id
        )
        db_sess.add(operation)
        db_sess.commit()
        return redirect('/')
    return render_template('add_operation.html', form=form)


@app.route("/operations", methods=["GET", "POST"])
@login_required
def operations():
    form = PeriodForm()
    page = int(request.args.get("page", 1))
    per_page = 10

    today = date.today()
    start_date = today.replace(day=1)
    end_date = today
    selected_type = 'all'
    selected_category = 'all'
    show_all = False
    search_query = ''

    user_operations = current_user.operations
    db_sess = db_session.create_session()

    user_categories = [{
        'id': c.id,
        'name': c.name,
        'type': c.type
    } for c in current_user.categories]

    base_categories = [{
        'id': c.id,
        'name': c.name,
        'type': c.type
    } for c in db_sess.query(Category).filter(Category.user_id == None)]

    all_categories = [{'id': 'all', 'name': 'Все', 'type': 'all'}]
    all_categories.extend(base_categories + user_categories)

    form.category.choices = [(str(c['id']), c['name']) for c in all_categories]

    if request.method == "POST":
        date_range_str = form.date_range.data

        selected_type = form.operation_type.data
        selected_category = form.category.data
        show_all = 'show_all' in request.form
        search_query = request.form.get('search_query', '')

        if not show_all and date_range_str:
            try:
                start_str, end_str = date_range_str.split(" to ")
                start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                return redirect("/operations")
    else:
        selected_category = request.args.get("selected_category", "all")
        selected_type = request.args.get("selected_type", "all")
        date_range_str = request.args.get("date_range")

        if date_range_str:
            try:
                start_str, end_str = date_range_str.split(" to ")
                start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d").date()
                end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                pass

        form.date_range.data = ' to '.join([f"{start_date}", f"{end_date}"])
        form.operation_type.data = selected_type
        form.category.data = selected_category

    operations_in_period = user_operations

    if not show_all:
        operations_in_period = filter(
            lambda op: start_date <= op.date.date() <= end_date,
            operations_in_period
        )

    if selected_type != 'all':
        operations_in_period = filter(lambda op: op.type == selected_type, operations_in_period)

    if selected_category != 'all':
        operations_in_period = filter(lambda op: str(op.category_id) == selected_category, operations_in_period)

    if search_query:
        operations_in_period = filter(lambda op: search_query.lower() in op.description.lower(), operations_in_period)

    operations_in_period = list(operations_in_period)
    operations_in_period.sort(key=lambda op: op.date, reverse=True)

    total_pages = math.ceil(len(operations_in_period) / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    current_ops = operations_in_period[start:end]

    return render_template(
        "operations.html",
        form=form,
        operations=current_ops,
        total_pages=total_pages,
        current_page=page,
        selected_type=selected_type,
        selected_category=selected_category,
        show_all=show_all,
        search_query=search_query,
        categories=all_categories
    )


@app.route('/edit_operation/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_operation(id):
    form = OperationForm()
    db_sess = db_session.create_session()
    operation = db_sess.query(Operation).filter(Operation.id == id, Operation.user_id == current_user.id).first()

    if not operation:
        abort(404)

    categories = db_sess.query(Category).filter(
        ((Category.user_id == None) | (Category.user_id == current_user.id)) &
        (Category.type == operation.type)
    ).all()
    form.category.choices = [(str(c.id), c.name) for c in categories]

    if request.method == "GET":
        form.date.data = operation.date
        form.amount.data = operation.amount
        form.category.data = str(operation.category_id)
        form.type.data = operation.type
        form.description.data = operation.description

    if form.validate_on_submit():
        operation.date = form.date.data
        operation.amount = form.amount.data
        operation.category_id = int(form.category.data)
        operation.type = form.type.data
        operation.description = form.description.data

        db_sess.commit()
        return redirect('/operations')

    return render_template('add_operation.html', title='Редактирование операции', form=form)


@app.route("/operations/delete/<int:id>", methods=["POST"])
@login_required
def delete_operation(id):
    db_sess = db_session.create_session()
    operation = db_sess.query(Operation).filter(Operation.id == id, Operation.user_id == current_user.id).first()
    if operation:
        db_sess.delete(operation)
        db_sess.commit()

    query_params = {
        "page": request.args.get("page", 1),
        "operation_type": request.args.get("operation_type", "all"),
        "show_all": request.args.get("show_all", ""),
        "search_query": request.args.get("search_query", "")
    }
    query_str = "&".join([f"{k}={v}" for k, v in query_params.items() if v])
    return redirect(f"/operations?{query_str}")


@app.route('/get_categories/<op_type>')
@login_required
def get_categories(op_type):
    db_sess = db_session.create_session()
    categories = db_sess.query(Category).filter(
        ((Category.user_id == None) | (Category.user_id == current_user.id)) &
        (Category.type == op_type)
    ).all()
    return jsonify([(cat.id, cat.name) for cat in categories])


@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    form = CategoryForm()
    db_sess = db_session.create_session()

    if form.validate_on_submit():
        new_category = Category(
            name=form.name.data,
            type=form.type.data,
            user_id=current_user.id
        )
        db_sess.add(new_category)
        db_sess.commit()

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '')
    show_my = request.args.get('show_my', '0') == '1'

    query = db_sess.query(Category)
    if search_query:
        query = query.filter(Category.name.ilike(f"%{search_query}%"))

    if show_my:
        query = query.filter(Category.user_id == current_user.id)
        categories_list = query.order_by(Category.name).all()
        base_categories = []
        user_categories = categories_list
    else:
        categories_list = query.order_by(Category.name).all()
        base_categories = [c for c in categories_list if c.user_id is None]
        user_categories = [c for c in categories_list if c.user_id == current_user.id]

    per_page = 10
    total_pages = math.ceil(len(user_categories) / per_page)
    user_categories = user_categories[(page - 1) * per_page: page * per_page]

    return render_template(
        "category_manager.html",
        base_categories=base_categories,
        user_categories=user_categories,
        current_page=page,
        total_pages=total_pages,
        search_query=search_query,
        show_my=show_my,
        form=form,
        title='Категории'
    )


@app.route('/delete_category/<int:id>', methods=['POST'])
@login_required
def delete_category(id):
    db_sess = db_session.create_session()
    category = db_sess.query(Category).filter(Category.id == id).first()

    if not category:
        abort(404)

    if category.user_id is None:
        return redirect('/categories')

    if category.user_id != current_user.id:
        abort(403)

    db_sess.query(Operation).filter(
        Operation.category_id == category.id,
        Operation.user_id == current_user.id
    ).delete(synchronize_session=False)

    db_sess.delete(category)
    db_sess.commit()

    page = request.form.get("page", "1")
    search_query = request.form.get("search_query", "")
    return redirect(f"/categories?page={page}&search={search_query}")


@app.route("/currency")
def currency_page():
    currencies = {"USD": 'Американский доллар', "EUR": 'Евро', "CNY": 'Китайский юань', "RUB": 'Российский рубль',
                  'TRY': 'Турецкая лира', 'AED': 'Арабский дирхамм', 'BYN': 'Белорусский рубль'}
    return render_template("currency_test.html", currencies=currencies, title='Конвертер валют')


@app.route("/currency/data", methods=["POST"])
def currency_data():
    data = load_data()
    from_curr = request.json.get("from_currency")
    to_curr = request.json.get("to_currency")
    amount = float(request.json.get("amount", 1))

    if from_curr not in data or to_curr not in data:
        return jsonify({"error": "Некорректные данные"}), 400

    common_times = sorted(set(data[from_curr]) & set(data[to_curr]))
    times = [datetime.fromisoformat(t).isoformat() for t in common_times]
    rates = [data[from_curr][t] / data[to_curr][t] for t in common_times]
    converted = amount * rates[-1] if rates else 0

    return jsonify({
        "converted": round(converted, 4),
        "graph": {
            "x": times,
            "y": rates,
            "from": from_curr,
            "to": to_curr
        }
    })


@app.route("/statistics")
@login_required
def statistics():
    date_range_str = request.args.get("date_range")
    if date_range_str:
        try:
            start_str, end_str = date_range_str.split(" to ")
            start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
            end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
        except ValueError:
            start_date = date.today().replace(day=1)
            end_date = date.today()
    else:
        start_date = date.today().replace(day=1)
        end_date = date.today()

    db_sess = db_session.create_session()

    all_categories = db_sess.query(Category).filter(
        (Category.user_id == None) | (Category.user_id == current_user.id)
    ).all()

    category_to_id = {cat.name: cat.id for cat in all_categories}

    expenses = db_sess.query(Operation).filter(
        Operation.user_id == current_user.id,
        Operation.type == "expense",
        Operation.date >= start_date,
        Operation.date <= end_date
    ).all()

    expense_by_category = {}
    for op in expenses:
        cat = next((c for c in all_categories if c.id == op.category_id), None)
        if cat:
            expense_by_category.setdefault(cat.name, 0)
            expense_by_category[cat.name] += op.amount

    incomes = db_sess.query(Operation).filter(
        Operation.user_id == current_user.id,
        Operation.type == "income",
        Operation.date >= start_date,
        Operation.date <= end_date
    ).all()

    expense_by_day = defaultdict(float)
    income_by_day = defaultdict(float)

    for op in expenses:
        date_str = op.date.strftime("%Y-%m-%d")
        expense_by_day[date_str] += op.amount

    for op in incomes:
        date_str = op.date.strftime("%Y-%m-%d")
        income_by_day[date_str] += op.amount

    all_days = sorted(set(expense_by_day.keys()) | set(income_by_day.keys()))

    day_labels = all_days
    day_expenses = [expense_by_day.get(day, 0) for day in all_days]
    day_incomes = [income_by_day.get(day, 0) for day in all_days]

    date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

    now = datetime.now()

    plans = db_sess.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.month == now.month,
        Budget.year == now.year
    ).all()
    plan_by_category_id = {plan.category_id: plan.planned_amount for plan in plans}

    comparison_rows = []
    for cat in all_categories:
        if cat.id in plan_by_category_id:
            fact = sum(op.amount for op in expenses if op.category_id == cat.id)
            plan = plan_by_category_id[cat.id]
            percent = (fact / plan) * 100 if plan else 0
            comparison_rows.append({
                "category": cat.name,
                "fact": round(fact, 2),
                "plan": round(plan, 2),
                "percent": round(percent, 1)
            })

    return render_template("statistics.html",
                           labels=list(expense_by_category.keys()),
                           values=list(expense_by_category.values()),
                           date_range=date_range,
                           category_to_id_map=category_to_id,
                           day_labels=day_labels,
                           day_expenses=day_expenses,
                           day_incomes=day_incomes,
                           comparison_rows=comparison_rows)


@app.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    session = db_session.create_session()
    form = BudgetForm()
    current_year = datetime.now().year
    current_month_num = datetime.now().month
    current_month_name = datetime.now().strftime("%B")

    existing_budgets = session.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.year == current_year,
        Budget.month == current_month_num
    ).all()

    if existing_budgets:
        return redirect("/")

    categories = session.query(Category).filter(
        ((Category.user_id == None) | (Category.user_id == current_user.id)) &
        (Category.type == "expense")
    ).all()

    categories_data = [{"id": c.id, "name": c.name} for c in categories]

    if request.method == "POST":
        try:
            for key in request.form:
                if key.startswith("category_"):
                    category_id = int(request.form.get(key))
                    amount = request.form.get(f"amount_{key.split('_')[1]}")
                    if amount:
                        budget = Budget(
                            user_id=current_user.id,
                            category_id=category_id,
                            year=current_year,
                            month=current_month_num,
                            planned_amount=float(amount)
                        )
                        session.add(budget)
            session.commit()
            return redirect("/budget")
        except Exception as e:
            session.rollback()
            return f"Ошибка при сохранении: {e}", 500

    return render_template("budget.html",
                           form=form,
                           categories=categories_data,
                           current_month=current_month_name)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    name_form = NameChangeForm()
    password_form = PasswordStepOneForm()
    image_form = UploadImageForm()

    if name_form.validate_on_submit():
        sess = db_session.create_session()
        current_user.username = name_form.username.data
        sess.commit()
        flash("Имя пользователя обновлено.", "success")
        return redirect(url_for("profile"))

    return render_template("profile.html", name_form=name_form, password_form=password_form, image_form=image_form)


@app.route("/change_password", methods=["POST", "GET"])
@login_required
def change_password():
    step1_form = PasswordStepOneForm()
    step2_form = PasswordStepTwoForm()

    if step1_form.validate_on_submit():
        if not current_user.check_password(step1_form.current_password.data):
            flash("Неверный текущий пароль.", "danger")
            return redirect(url_for("profile"))

        return render_template("change_password_step2.html", form=step2_form)

    return redirect(url_for("profile"))


@app.route("/change_password_step2", methods=["POST"])
@login_required
def change_password_step2():
    form = PasswordStepTwoForm()
    if form.validate_on_submit():
        sess = db_session.create_session()
        current_user.set_password(form.new_password.data)
        sess.commit()
        flash("Пароль успешно изменён.", "success")
        return redirect(url_for("profile"))

    return render_template("change_password_step2.html", form=form)


@app.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    form = UploadImageForm()
    if form.validate_on_submit():
        file = form.image.data
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1].lower()

        new_filename = f'user_{current_user.id}.jpg'
        file_path = os.path.join('static/avatars', new_filename)

        try:
            img = Image.open(file)

            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 2
            right = (width + min_dim) / 2
            bottom = (height + min_dim) / 2
            img_cropped = img.crop((left, top, right, bottom))

            img_resized = img_cropped.resize((500, 500))
            img_resized.save(file_path)
            db_sess = db_session.create_session()
            user = db_sess.get(User, current_user.id)

            user.image_path = f'avatars/{new_filename}'
            db_sess.commit()

        except Exception as e:
            print("ошибка обработки изображения", e)

    return redirect(url_for('profile'))


@app.route("/calculators")
@login_required
def calculators_page():
    return render_template("calculators.html", title='Калькуляторы')


@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def calculate_deposit():
    is_table = False
    form = DepositCalculatorForm()
    if form.validate_on_submit():
        is_table = True
        list_of_charges = []
        name = request.form["name"]
        date_open = request.form["date"]
        date = datetime(int(date_open[:4]), int(date_open[5:7]), int(date_open[8:]))
        is_end_day = False
        if int(date.day) == int(monthrange(date.year, date.month)[1]):
            is_end_day = True
        amount = request.form["amount"]
        percent = request.form["percent"]
        term = request.form["term"]
        type_term = request.form["type_term"]
        if type_term == 'year':
            term = int(term) * 12
        result = round(int(amount) * (1 + ((int(percent) / 100) / 12)) ** int(term), 2)
        income = round(result - int(amount), 2)
        for _ in range(int(term)):
            charge = round((int(amount) * (1 + ((int(percent) / 100) / 12)) ** 1) - int(amount), 2)
            amount = (int(amount) * (1 + ((int(percent) / 100) / 12)) ** 1)
            date = date + relativedelta(months=1)
            if int(monthrange(date.year, date.month)[1]) > int(date.day) and is_end_day:
                date = datetime(date.year, date.month, int(monthrange(date.year, date.month)[1]))
            list_of_charges.append([str(date)[:10], str(charge)])
        return render_template('deposit_calculator.html', form=form, income=income,
                               amount_received=result, title="Депозитный калькулятор", list_of_charges=list_of_charges,
                               is_table=is_table, name_file=name)
    return render_template('deposit_calculator.html', form=form, title="Депозитный калькулятор",
                           is_table=is_table)


@app.route("/credit", methods=['GET', 'POST'])
@login_required
def credit_page():
    is_table = False
    form = CreditCalculatorForm()
    if form.validate_on_submit():
        repayment_list = []
        name = request.form["name"]
        amount = int(request.form["amount"])
        credit_amount = amount
        income = amount
        percent = int(request.form["percent"])
        term = int(request.form["term"])
        type_term = request.form["type_term"]
        date_open = request.form["date"]
        date = datetime(int(date_open[:4]), int(date_open[5:7]), int(date_open[8:]))
        is_end_day = False
        if int(date.day) == int(monthrange(date.year, date.month)[1]):
            is_end_day = True
        p = (percent / 100) / 12
        if type_term == "year":
            term = int(term) * 12
        monthly_payment = amount * ((p * ((1 + p) ** term)) / (((1 + p) ** term) - 1))
        for _ in range(term):
            date = date + relativedelta(months=1)
            if isleap(date.year):
                days = 366
            else:
                days = 365
            if int(monthrange(date.year, date.month)[1]) > int(date.day) and is_end_day:
                date = datetime(date.year, date.month, int(monthrange(date.year, date.month)[1]))
            repayment_of_interest = (credit_amount * ((percent / 100) / days)) * int(
                monthrange(date.year, date.month)[1])
            income += repayment_of_interest
            credit_amount = credit_amount - (monthly_payment - repayment_of_interest)
            repayment_list.append([str(date)[:10], round(monthly_payment, 2), round(repayment_of_interest, 2),
                                   round(monthly_payment - repayment_of_interest, 2), round(credit_amount, 2)])
        income = round(income, 2)
        result = round(income - amount, 2)
        is_table = True
        return render_template('credit_calculator.html', form=form, income=income,
                               amount_received=result, title="Кредитный калькулятор", is_table=is_table,
                               repayment_list=repayment_list, name_file=name)
    return render_template('credit_calculator.html', form=form, title="Кредитный калькулятор",
                           is_table=is_table)


@app.route('/savings', methods=['POST', 'GET'])
@login_required
def saving_cal_page():
    form = SavingsCalculatorForm()
    is_table = False
    if form.validate_on_submit():
        is_table = True
        denominator = 1
        list_of_savings = []
        name_file = request.form["name"]
        date_open = request.form["date"]
        date = datetime(int(date_open[:4]), int(date_open[5:7]), int(date_open[8:]))
        amount = int(request.form["amount"])
        payment_type = request.form["payment_type"]
        quantity = int(request.form["quantity"])
        type_repayment = request.form["type_repayment"]
        if type_repayment == "month":
            if payment_type == "day":
                denominator = 30 * quantity
            elif payment_type == "week":
                denominator = 4 * quantity
            elif payment_type == "month":
                denominator = quantity
        elif type_repayment == "year":
            if payment_type == "day":
                denominator = 365 * quantity
            elif payment_type == "week":
                denominator = 48 * quantity
            elif payment_type == "month":
                denominator = 12 * quantity
        result = round(amount / denominator, 2)
        for _ in range(denominator):
            if payment_type == "day":
                date = date + relativedelta(days=1)
                print(date)
                list_of_savings.append([str(date)[:10], result])
            elif payment_type == "week":
                date = date + relativedelta(days=7)
                list_of_savings.append([str(date)[:10], result])
            elif payment_type == "month":
                date = date + relativedelta(months=1)
                list_of_savings.append([str(date)[:10], result])
        return render_template("savings_calculator.html", form=form, title="Калькулятор сохранений",
                               result=result, is_table=is_table, amount=amount, name_file=name_file,
                               list_of_savings=list_of_savings)
    return render_template("savings_calculator.html", form=form, title="Калькулятор сохранений",
                           is_table=is_table)


if __name__ == '__main__':
    main()
