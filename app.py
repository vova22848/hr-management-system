from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from database import Database
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production-2024'
db = Database()


# ---------------------- ГЛАВНАЯ СТРАНИЦА (ДАШБОРД) ----------------------
@app.route('/')
def index():
    # Статистика для дашборда
    total_employees = len(db.fetch_all("SELECT * FROM employees WHERE is_active = 1"))
    total_departments = len(db.fetch_all("SELECT * FROM departments"))
    total_positions = len(db.fetch_all("SELECT * FROM positions"))

    # Последние приказы
    recent_orders = db.fetch_all("""
        SELECT o.order_number, o.order_type, o.order_date, 
               e.last_name || ' ' || e.first_name as employee_name
        FROM orders o
        JOIN employees e ON o.employee_id = e.id
        ORDER BY o.order_date DESC
        LIMIT 5
    """)

    # Данные для графика распределения по подразделениям
    dept_stats = db.fetch_all("""
        SELECT d.name, COUNT(e.id) as count
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.id AND e.is_active = 1
        GROUP BY d.id
        ORDER BY count DESC
    """)

    # Предстоящие отпуска
    upcoming_vacations = db.fetch_all("""
        SELECT e.last_name || ' ' || e.first_name as employee_name,
               v.start_date, v.end_date, v.vacation_type
        FROM vacations v
        JOIN employees e ON v.employee_id = e.id
        WHERE v.start_date >= date('now')
        ORDER BY v.start_date
        LIMIT 5
    """)

    return render_template('index.html',
                           total_employees=total_employees,
                           total_departments=total_departments,
                           total_positions=total_positions,
                           recent_orders=recent_orders,
                           dept_stats=dept_stats,
                           upcoming_vacations=upcoming_vacations)


# ---------------------- УПРАВЛЕНИЕ СОТРУДНИКАМИ ----------------------
@app.route('/employees')
def employees():
    employees = db.fetch_all("""
        SELECT e.*, p.title as position_title, d.name as department_name
        FROM employees e
        LEFT JOIN positions p ON e.position_id = p.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.is_active = 1
        ORDER BY e.last_name, e.first_name
    """)

    departments = db.fetch_all("SELECT * FROM departments ORDER BY name")
    positions = db.fetch_all("SELECT * FROM positions ORDER BY title")

    return render_template('employees.html',
                           employees=employees,
                           departments=departments,
                           positions=positions)


@app.route('/employee/add', methods=['POST'])
def add_employee():
    try:
        data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'patronymic': request.form.get('patronymic', ''),
            'birth_date': request.form.get('birth_date') or None,
            'gender': request.form.get('gender') or None,
            'phone': request.form.get('phone') or None,
            'email': request.form.get('email') or None,
            'hire_date': request.form['hire_date'],
            'position_id': int(request.form['position_id']) if request.form.get('position_id') else None,
            'department_id': int(request.form['department_id']) if request.form.get('department_id') else None,
            'is_active': 1
        }

        # Формируем INSERT запрос
        fields = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO employees ({fields}) VALUES ({placeholders})"

        cursor = db.execute(query, tuple(data.values()))
        emp_id = cursor.lastrowid

        # Создаем приказ о приеме
        order_number = f"ПР-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        db.execute("""
            INSERT INTO orders (order_number, order_type, description, employee_id, order_date, effective_date)
            VALUES (?, 'прием', ?, ?, date('now'), ?)
        """, (order_number, f"Прием на работу сотрудника {data['first_name']} {data['last_name']}", emp_id,
              data['hire_date']))

        flash('Сотрудник успешно добавлен!', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении сотрудника: {str(e)}', 'danger')

    return redirect(url_for('employees'))


@app.route('/employee/<int:emp_id>/fire', methods=['POST'])
def fire_employee(emp_id):
    try:
        # Получаем данные сотрудника
        emp = db.fetch_one("SELECT first_name, last_name FROM employees WHERE id = ?", (emp_id,))

        # Увольняем
        db.execute("""
            UPDATE employees 
            SET is_active = 0, fire_date = date('now') 
            WHERE id = ?
        """, (emp_id,))

        # Создаем приказ об увольнении
        order_number = f"УВ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        db.execute("""
            INSERT INTO orders (order_number, order_type, description, employee_id, order_date, effective_date)
            VALUES (?, 'увольнение', ?, ?, date('now'), date('now'))
        """, (order_number, f"Увольнение сотрудника {emp['first_name']} {emp['last_name']}", emp_id))

        flash('Сотрудник уволен', 'info')
    except Exception as e:
        flash(f'Ошибка при увольнении: {str(e)}', 'danger')

    return redirect(url_for('employees'))


# ---------------------- ПОДРАЗДЕЛЕНИЯ ----------------------
@app.route('/departments')
def departments():
    departments = db.fetch_all("""
        SELECT d.*, 
               e.last_name || ' ' || e.first_name as manager_name,
               (SELECT COUNT(*) FROM employees WHERE department_id = d.id AND is_active = 1) as employee_count
        FROM departments d
        LEFT JOIN employees e ON d.manager_id = e.id
        ORDER BY d.name
    """)

    employees = db.fetch_all("""
        SELECT id, last_name || ' ' || first_name as full_name 
        FROM employees 
        WHERE is_active = 1 
        ORDER BY last_name
    """)

    return render_template('departments.html',
                           departments=departments,
                           employees=employees)


@app.route('/department/add', methods=['POST'])
def add_department():
    try:
        name = request.form['name']
        manager_id = request.form.get('manager_id')
        manager_id = int(manager_id) if manager_id else None

        db.execute("INSERT INTO departments (name, manager_id) VALUES (?, ?)",
                   (name, manager_id))

        flash('Подразделение добавлено!', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении подразделения: {str(e)}', 'danger')

    return redirect(url_for('departments'))


@app.route('/department/<int:dept_id>/delete', methods=['POST'])
def delete_department(dept_id):
    try:
        # Проверяем, есть ли сотрудники в подразделении
        emp_count = db.fetch_one("SELECT COUNT(*) as count FROM employees WHERE department_id = ? AND is_active = 1",
                                 (dept_id,))
        if emp_count and emp_count['count'] > 0:
            return jsonify({'success': False,
                            'message': f'Нельзя удалить подразделение, в котором работает {emp_count["count"]} сотрудников'})

        db.execute("DELETE FROM departments WHERE id = ?", (dept_id,))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ---------------------- ДОЛЖНОСТИ ----------------------
@app.route('/positions')
def positions():
    positions = db.fetch_all("""
        SELECT p.*, d.name as department_name,
               (SELECT COUNT(*) FROM employees WHERE position_id = p.id AND is_active = 1) as employee_count
        FROM positions p
        LEFT JOIN departments d ON p.department_id = d.id
        ORDER BY p.title
    """)

    departments = db.fetch_all("SELECT * FROM departments ORDER BY name")

    return render_template('positions.html',
                           positions=positions,
                           departments=departments)


@app.route('/position/add', methods=['POST'])
def add_position():
    try:
        title = request.form['title']
        base_salary = float(request.form['base_salary'])
        department_id = request.form.get('department_id')
        department_id = int(department_id) if department_id else None

        db.execute("""
            INSERT INTO positions (title, base_salary, department_id) 
            VALUES (?, ?, ?)
        """, (title, base_salary, department_id))

        flash('Должность добавлена!', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении должности: {str(e)}', 'danger')

    return redirect(url_for('positions'))


@app.route('/position/<int:pos_id>/delete', methods=['POST'])
def delete_position(pos_id):
    try:
        # Проверяем, есть ли сотрудники на должности
        emp_count = db.fetch_one("SELECT COUNT(*) as count FROM employees WHERE position_id = ? AND is_active = 1",
                                 (pos_id,))
        if emp_count and emp_count['count'] > 0:
            return jsonify({'success': False,
                            'message': f'Нельзя удалить должность, которую занимают {emp_count["count"]} сотрудников'})

        db.execute("DELETE FROM positions WHERE id = ?", (pos_id,))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ---------------------- ПРИКАЗЫ ----------------------
@app.route('/orders')
def orders():
    orders = db.fetch_all("""
        SELECT o.*, 
               e.last_name || ' ' || e.first_name as employee_name
        FROM orders o
        JOIN employees e ON o.employee_id = e.id
        ORDER BY o.order_date DESC
    """)

    return render_template('orders.html', orders=orders)


@app.route('/order/add', methods=['POST'])
def add_order():
    try:
        order_type = request.form['order_type']
        description = request.form['description']
        employee_id = int(request.form['employee_id'])
        effective_date = request.form.get('effective_date') or datetime.now().strftime('%Y-%m-%d')

        order_number = f"{order_type[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        db.execute("""
            INSERT INTO orders (order_number, order_type, description, employee_id, order_date, effective_date)
            VALUES (?, ?, ?, ?, date('now'), ?)
        """, (order_number, order_type, description, employee_id, effective_date))

        flash('Приказ создан!', 'success')
    except Exception as e:
        flash(f'Ошибка при создании приказа: {str(e)}', 'danger')

    return redirect(url_for('orders'))


# ---------------------- ОТПУСКА ----------------------
@app.route('/vacations')
def vacations():
    vacations = db.fetch_all("""
        SELECT v.*, 
               e.last_name || ' ' || e.first_name as employee_name
        FROM vacations v
        JOIN employees e ON v.employee_id = e.id
        WHERE e.is_active = 1
        ORDER BY v.start_date DESC
    """)

    employees = db.fetch_all("""
        SELECT id, last_name || ' ' || first_name as full_name 
        FROM employees 
        WHERE is_active = 1 
        ORDER BY last_name
    """)

    return render_template('vacations.html',
                           vacations=vacations,
                           employees=employees)


@app.route('/vacation/add', methods=['POST'])
def add_vacation():
    try:
        employee_id = int(request.form['employee_id'])
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        vacation_type = request.form['vacation_type']

        # Добавляем отпуск
        cursor = db.execute("""
            INSERT INTO vacations (employee_id, start_date, end_date, vacation_type, approved)
            VALUES (?, ?, ?, ?, 1)
        """, (employee_id, start_date, end_date, vacation_type))

        vac_id = cursor.lastrowid

        # Создаем приказ
        order_number = f"ОТП-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        emp = db.fetch_one("SELECT first_name, last_name FROM employees WHERE id = ?", (employee_id,))

        db.execute("""
            INSERT INTO orders (order_number, order_type, description, employee_id, order_date, effective_date)
            VALUES (?, 'отпуск', ?, ?, date('now'), ?)
        """, (order_number, f"Отпуск ({vacation_type}) сотрудника {emp['first_name']} {emp['last_name']}", employee_id,
              start_date))

        flash('Отпуск оформлен!', 'success')
    except Exception as e:
        flash(f'Ошибка при оформлении отпуска: {str(e)}', 'danger')

    return redirect(url_for('vacations'))


# ---------------------- ОТЧЕТЫ ----------------------
@app.route('/reports')
def reports():
    # Данные для отчетов
    dept_distribution = db.fetch_all("""
        SELECT d.name, COUNT(e.id) as count
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.id AND e.is_active = 1
        GROUP BY d.id
        ORDER BY count DESC
    """)

    gender_distribution = db.fetch_all("""
        SELECT gender, COUNT(*) as count
        FROM employees
        WHERE is_active = 1 AND gender IS NOT NULL
        GROUP BY gender
    """)

    age_stats = db.fetch_all("""
        SELECT 
            CASE 
                WHEN (strftime('%Y', 'now') - strftime('%Y', birth_date)) < 25 THEN 'до 25'
                WHEN (strftime('%Y', 'now') - strftime('%Y', birth_date)) BETWEEN 25 AND 35 THEN '25-35'
                WHEN (strftime('%Y', 'now') - strftime('%Y', birth_date)) BETWEEN 36 AND 45 THEN '36-45'
                WHEN (strftime('%Y', 'now') - strftime('%Y', birth_date)) BETWEEN 46 AND 55 THEN '46-55'
                ELSE 'старше 55'
            END as age_group,
            COUNT(*) as count
        FROM employees
        WHERE is_active = 1 AND birth_date IS NOT NULL
        GROUP BY age_group
        ORDER BY age_group
    """)

    return render_template('reports.html',
                           dept_distribution=dept_distribution,
                           gender_distribution=gender_distribution,
                           age_stats=age_stats)


# ---------------------- API для AJAX запросов ----------------------
@app.route('/api/employee/<int:emp_id>')
def get_employee(emp_id):
    employee = db.fetch_one("""
        SELECT e.*, p.title as position_title, d.name as department_name
        FROM employees e
        LEFT JOIN positions p ON e.position_id = p.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.id = ?
    """, (emp_id,))

    if employee:
        return jsonify(employee)
    return jsonify({'error': 'Сотрудник не найден'}), 404


@app.route('/api/stats')
def get_stats():
    stats = {
        'total_employees': len(db.fetch_all("SELECT * FROM employees WHERE is_active = 1")),
        'total_departments': len(db.fetch_all("SELECT * FROM departments")),
        'total_positions': len(db.fetch_all("SELECT * FROM positions")),
        'total_orders': len(db.fetch_all("SELECT * FROM orders")),
        'upcoming_vacations': len(db.fetch_all("""
            SELECT * FROM vacations 
            WHERE start_date >= date('now') 
            AND start_date <= date('now', '+30 days')
        """))
    }
    return jsonify(stats)


# ---------------------- ЗАПУСК ПРИЛОЖЕНИЯ ----------------------
if __name__ == '__main__':
    # Создаем папку templates если её нет
    if not os.path.exists('templates'):
        os.makedirs('templates')

    print("=" * 50)
    print("🚀 АРМ Начальника отдела кадров запущен!")
    print("📍 Откройте браузер и перейдите по адресу: http://127.0.0.1:5000")
    print("=" * 50)

    app.run(debug=True, host='127.0.0.1', port=5000)