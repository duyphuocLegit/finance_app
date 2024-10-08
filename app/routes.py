from app import app, db
from app.forms import RegistrationForm, LoginForm, TransactionForm,FilterForm
from app.models import User, Transaction
from flask_login import login_user, logout_user, login_required, current_user
from flask import render_template, redirect, url_for, flash, request,jsonify
from flask_paginate import Pagination, get_page_parameter
from datetime import datetime
from collections import defaultdict


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = FilterForm()
    transactions_query = Transaction.query.filter_by(user_id=current_user.id)

    if form.validate_on_submit():
        if form.start_date.data:
            transactions_query = transactions_query.filter(Transaction.date >= form.start_date.data)
        if form.end_date.data:
            transactions_query = transactions_query.filter(Transaction.date <= form.end_date.data)
        if form.category.data:
            transactions_query = transactions_query.filter(Transaction.category.ilike(f'%{form.category.data}%'))

    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = 10
    transactions_pagination = transactions_query.paginate(page=page, per_page=per_page, error_out=False)
    transactions = transactions_pagination.items
    total = transactions_pagination.total

    total_income = sum(t.amount for t in transactions if t.type == 'Income')
    total_expenses = sum(t.amount for t in transactions if t.type == 'Expense')
    balance = total_income - total_expenses

    # Prepare data for the chart
    income_data = defaultdict(float)
    expense_data = defaultdict(float)
    for t in transactions:
        date_str = t.date.strftime('%d-%m-%Y')
        if t.type == 'Income':
            income_data[date_str] += t.amount
        elif t.type == 'Expense':
            expense_data[date_str] += t.amount

    labels = sorted(set(income_data.keys()).union(expense_data.keys()))
    income_values = [income_data[label] for label in labels]
    expense_values = [expense_data[label] for label in labels]

    pagination = Pagination(page=page, total=total, per_page=per_page, css_framework='bootstrap4')

    return render_template('dashboard.html', transactions=transactions, total_income=total_income, total_expenses=total_expenses, balance=balance, form=form, pagination=pagination, labels=labels, income_values=income_values, expense_values=expense_values)

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        transaction = Transaction(
            title=form.title.data,
            amount=form.amount.data,
            type=form.type.data,
            date=form.date.data,
            category=form.category.data,
            user_id=current_user.id
        )
        db.session.add(transaction)
        db.session.commit()
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_transaction.html', form=form)

@app.route('/edit_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    transaction.title = data['title']
    transaction.amount = data['amount']
    transaction.type = data['type']
    transaction.date = datetime.strptime(data['date'], '%d-%m-%Y')
    transaction.category = data['category']
    db.session.commit()

    return jsonify({'success': 'Transaction updated successfully'})

@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != current_user.id:
        flash('You do not have permission to delete this transaction.', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('dashboard'))