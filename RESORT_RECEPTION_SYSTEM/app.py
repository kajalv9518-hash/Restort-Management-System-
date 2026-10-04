from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "resort_secret_key"

DB_NAME = "resort.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    # =====================================================
    # CUSTOMERS TABLE
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            room TEXT NOT NULL,
            room_type TEXT NOT NULL,
            checkin_date TEXT NOT NULL,
            checkout_date TEXT,
            charge REAL NOT NULL,
            payment_method TEXT DEFAULT 'Pending',
            payment_status TEXT DEFAULT 'Pending'
        )
    """)

    # =====================================================
    # ROOMS TABLE
    # =====================================================

    conn.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_no TEXT NOT NULL UNIQUE,
            room_type TEXT NOT NULL,
            charge REAL NOT NULL,
            status TEXT DEFAULT 'Available'
        )
    """)

    # =====================================================
    # DEFAULT ROOMS
    # =====================================================

    room_count = conn.execute(
        "SELECT COUNT(*) FROM rooms"
    ).fetchone()[0]

    if room_count == 0:

        rooms = [
            ("101", "AC", 5000),
            ("102", "AC", 5000),
            ("103", "AC", 5000),
            ("104", "Non-AC", 3000),
            ("105", "Non-AC", 3000),
            ("106", "Non-AC", 3000)
        ]

        for room_no, room_type, charge in rooms:

            conn.execute("""
                INSERT INTO rooms
                (room_no, room_type, charge, status)
                VALUES (?, ?, ?, 'Available')
            """, (
                room_no,
                room_type,
                charge
            ))

    conn.commit()
    conn.close()


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def home():

    conn = get_db()

    total_customers = conn.execute("""
        SELECT COUNT(*)
        FROM customers
    """).fetchone()[0]

    total_rooms = conn.execute("""
        SELECT COUNT(*)
        FROM rooms
    """).fetchone()[0]

    available_rooms = conn.execute("""
        SELECT COUNT(*)
        FROM rooms
        WHERE status = 'Available'
    """).fetchone()[0]

    occupied_rooms = conn.execute("""
        SELECT COUNT(*)
        FROM rooms
        WHERE status = 'Occupied'
    """).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        total_customers=total_customers,
        total_rooms=total_rooms,
        available_rooms=available_rooms,
        occupied_rooms=occupied_rooms
    )


# =========================================================
# CHECK-IN
# =========================================================

@app.route("/checkin", methods=["GET", "POST"])
def checkin():

    conn = get_db()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        room = request.form.get("room", "").strip()
        checkin_date = request.form.get(
            "checkin_date",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not name or not mobile or not room or not checkin_date:

            rooms = conn.execute("""
                SELECT *
                FROM rooms
                WHERE status = 'Available'
                ORDER BY room_no
            """).fetchall()

            conn.close()

            return render_template(
                "checkin.html",
                rooms=rooms,
                error="Please fill all fields."
            )

        # -------------------------------------------------
        # FIND ROOM
        # -------------------------------------------------

        room_data = conn.execute("""
            SELECT *
            FROM rooms
            WHERE room_no = ?
        """, (room,)).fetchone()

        if not room_data:

            rooms = conn.execute("""
                SELECT *
                FROM rooms
                WHERE status = 'Available'
                ORDER BY room_no
            """).fetchall()

            conn.close()

            return render_template(
                "checkin.html",
                rooms=rooms,
                error="Selected room does not exist."
            )

        # -------------------------------------------------
        # ROOM STATUS
        # -------------------------------------------------

        if room_data["status"] != "Available":

            rooms = conn.execute("""
                SELECT *
                FROM rooms
                WHERE status = 'Available'
                ORDER BY room_no
            """).fetchall()

            conn.close()

            return render_template(
                "checkin.html",
                rooms=rooms,
                error=f"Room {room} is already occupied."
            )

        room_type = room_data["room_type"]
        charge = float(room_data["charge"])

        # -------------------------------------------------
        # ADD CUSTOMER
        # -------------------------------------------------

        conn.execute("""
            INSERT INTO customers
            (
                name,
                mobile,
                room,
                room_type,
                checkin_date,
                checkout_date,
                charge,
                payment_method,
                payment_status
            )
            VALUES (?, ?, ?, ?, ?, NULL, ?, 'Pending', 'Pending')
        """, (
            name,
            mobile,
            room,
            room_type,
            checkin_date,
            charge
        ))

        # -------------------------------------------------
        # ROOM OCCUPIED
        # -------------------------------------------------

        conn.execute("""
            UPDATE rooms
            SET status = 'Occupied'
            WHERE room_no = ?
        """, (room,))

        conn.commit()
        conn.close()

        return render_template(
            "checkin.html",
            success=True,
            name=name,
            mobile=mobile,
            room=room,
            room_type=room_type,
            checkin_date=checkin_date,
            charge=charge
        )

    # -----------------------------------------------------
    # GET AVAILABLE ROOMS
    # -----------------------------------------------------

    rooms = conn.execute("""
        SELECT *
        FROM rooms
        WHERE status = 'Available'
        ORDER BY room_no
    """).fetchall()

    conn.close()

    return render_template(
        "checkin.html",
        rooms=rooms
    )


# =========================================================
# CUSTOMER RECORDS
# =========================================================

@app.route("/customers")
def customers():

    conn = get_db()

    search = request.args.get(
        "search",
        ""
    ).strip()

    if search:

        customers_data = conn.execute("""
            SELECT
                id,
                name,
                mobile,
                room,
                room_type,
                checkin_date,
                checkout_date,
                charge,
                payment_method,
                payment_status
            FROM customers
            WHERE
                name LIKE ?
                OR mobile LIKE ?
                OR room LIKE ?
            ORDER BY id DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        )).fetchall()

    else:

        customers_data = conn.execute("""
            SELECT
                id,
                name,
                mobile,
                room,
                room_type,
                checkin_date,
                checkout_date,
                charge,
                payment_method,
                payment_status
            FROM customers
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    return render_template(
        "customers.html",
        customers=customers_data,
        search=search
    )


# =========================================================
# DELETE CUSTOMER
# =========================================================

@app.route(
    "/delete_customer/<int:customer_id>",
    methods=["POST"]
)
def delete_customer(customer_id):

    conn = get_db()

    # -----------------------------------------------------
    # FIND CUSTOMER ROOM
    # -----------------------------------------------------

    customer = conn.execute("""
        SELECT room
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:

        conn.close()

        return """
        <h2>Customer not found.</h2>
        <br>
        <a href="/customers">
            Back to Customer Records
        </a>
        """, 404

    room = customer["room"]

    # -----------------------------------------------------
    # DELETE CUSTOMER
    # -----------------------------------------------------

    conn.execute("""
        DELETE FROM customers
        WHERE id = ?
    """, (customer_id,))

    # -----------------------------------------------------
    # MAKE ROOM AVAILABLE
    # -----------------------------------------------------

    conn.execute("""
        UPDATE rooms
        SET status = 'Available'
        WHERE room_no = ?
    """, (room,))

    conn.commit()
    conn.close()

    return redirect("/customers")


# =========================================================
# ROOM MANAGEMENT
# =========================================================

@app.route("/rooms", methods=["GET", "POST"])
def rooms():

    conn = get_db()

    # =====================================================
    # ADD NEW ROOM
    # =====================================================

    if request.method == "POST":

        room_no = request.form.get(
            "room_no",
            ""
        ).strip()

        room_type = request.form.get(
            "room_type",
            ""
        ).strip()

        charge = request.form.get(
            "charge",
            ""
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not room_no or not room_type or not charge:

            rooms_data = conn.execute("""
                SELECT *
                FROM rooms
                ORDER BY room_no
            """).fetchall()

            conn.close()

            return render_template(
                "rooms.html",
                rooms=rooms_data,
                error="Please fill all room details."
            )

        # -------------------------------------------------
        # DUPLICATE ROOM
        # -------------------------------------------------

        existing_room = conn.execute("""
            SELECT *
            FROM rooms
            WHERE room_no = ?
        """, (room_no,)).fetchone()

        if existing_room:

            rooms_data = conn.execute("""
                SELECT *
                FROM rooms
                ORDER BY room_no
            """).fetchall()

            conn.close()

            return render_template(
                "rooms.html",
                rooms=rooms_data,
                error=f"Room {room_no} already exists."
            )

        # -------------------------------------------------
        # VALIDATE CHARGE
        # -------------------------------------------------

        try:

            charge_value = float(charge)

            if charge_value < 0:
                raise ValueError

        except ValueError:

            rooms_data = conn.execute("""
                SELECT *
                FROM rooms
                ORDER BY room_no
            """).fetchall()

            conn.close()

            return render_template(
                "rooms.html",
                rooms=rooms_data,
                error="Please enter a valid room charge."
            )

        # -------------------------------------------------
        # INSERT ROOM
        # -------------------------------------------------

        conn.execute("""
            INSERT INTO rooms
            (
                room_no,
                room_type,
                charge,
                status
            )
            VALUES (?, ?, ?, 'Available')
        """, (
            room_no,
            room_type,
            charge_value
        ))

        conn.commit()

        # -------------------------------------------------
        # UPDATED ROOM LIST
        # -------------------------------------------------

        rooms_data = conn.execute("""
            SELECT
                id,
                room_no,
                room_type,
                charge,
                status
            FROM rooms
            ORDER BY room_no
        """).fetchall()

        conn.close()

        return render_template(
            "rooms.html",
            rooms=rooms_data,
            success=f"Room {room_no} added successfully!"
        )

    # =====================================================
    # DISPLAY ROOMS
    # =====================================================

    rooms_data = conn.execute("""
        SELECT
            id,
            room_no,
            room_type,
            charge,
            status
        FROM rooms
        ORDER BY room_no
    """).fetchall()

    conn.close()

    return render_template(
        "rooms.html",
        rooms=rooms_data
    )


# =========================================================
# CHECKOUT
# =========================================================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    conn = get_db()

    if request.method == "POST":

        room = request.form.get(
            "room",
            ""
        ).strip()

        customer = conn.execute("""
            SELECT *
            FROM customers
            WHERE room = ?
            AND checkout_date IS NULL
            ORDER BY id DESC
            LIMIT 1
        """, (room,)).fetchone()

        if not customer:

            conn.close()

            return render_template(
                "checkout.html",
                error=f"No active customer found in Room {room}."
            )

        checkout_date = datetime.now().strftime(
            "%Y-%m-%d"
        )

        # -------------------------------------------------
        # UPDATE CUSTOMER
        # -------------------------------------------------

        conn.execute("""
            UPDATE customers
            SET
                checkout_date = ?,
                payment_status = 'Pending'
            WHERE id = ?
        """, (
            checkout_date,
            customer["id"]
        ))

        # -------------------------------------------------
        # ROOM AVAILABLE
        # -------------------------------------------------

        conn.execute("""
            UPDATE rooms
            SET status = 'Available'
            WHERE room_no = ?
        """, (room,))

        conn.commit()

        updated_customer = conn.execute("""
            SELECT *
            FROM customers
            WHERE id = ?
        """, (
            customer["id"],
        )).fetchone()

        conn.close()

        return render_template(
            "checkout.html",
            success=True,
            customer=updated_customer
        )

    # -----------------------------------------------------
    # OCCUPIED ROOMS
    # -----------------------------------------------------

    occupied_rooms = conn.execute("""
        SELECT *
        FROM rooms
        WHERE status = 'Occupied'
        ORDER BY room_no
    """).fetchall()

    conn.close()

    return render_template(
        "checkout.html",
        rooms=occupied_rooms
    )


# =========================================================
# BILLING
# =========================================================

@app.route("/billing", methods=["GET", "POST"])
def billing():

    conn = get_db()

    if request.method == "POST":

        room = request.form.get(
            "room",
            ""
        ).strip()

        payment_method = request.form.get(
            "payment_method",
            "Cash"
        )

        customer = conn.execute("""
            SELECT *
            FROM customers
            WHERE room = ?
            AND checkout_date IS NOT NULL
            ORDER BY id DESC
            LIMIT 1
        """, (room,)).fetchone()

        if not customer:

            conn.close()

            return render_template(
                "billing.html",
                error=(
                    f"No completed checkout found "
                    f"for Room {room}."
                )
            )

        # -------------------------------------------------
        # CALCULATE STAY DAYS
        # -------------------------------------------------

        try:

            checkin_date = datetime.strptime(
                customer["checkin_date"],
                "%Y-%m-%d"
            )

            checkout_date = datetime.strptime(
                customer["checkout_date"],
                "%Y-%m-%d"
            )

            days = (
                checkout_date.date()
                - checkin_date.date()
            ).days

            if days <= 0:
                days = 1

        except Exception:

            days = 1

        # -------------------------------------------------
        # BILL
        # -------------------------------------------------

        room_total = (
            float(customer["charge"])
            * days
        )

        gst = room_total * 0.05

        grand_total = room_total + gst

        # -------------------------------------------------
        # PAYMENT UPDATE
        # -------------------------------------------------

        conn.execute("""
            UPDATE customers
            SET
                payment_method = ?,
                payment_status = 'Paid'
            WHERE id = ?
        """, (
            payment_method,
            customer["id"]
        ))

        conn.commit()

        # Get updated customer
        customer = conn.execute("""
            SELECT *
            FROM customers
            WHERE id = ?
        """, (
            customer["id"],
        )).fetchone()

        conn.close()

        return render_template(
            "billing_result.html",
            customer=customer,
            days=days,
            room_total=room_total,
            gst=gst,
            grand_total=grand_total,
            payment_method=payment_method
        )

    conn.close()

    return render_template(
        "billing.html"
    )


# =========================================================
# PAYMENTS
# =========================================================

@app.route("/payments", methods=["GET", "POST"])
def payments():

    conn = get_db()

    if request.method == "POST":

        room = request.form.get(
            "room",
            ""
        ).strip()

        payment_method = request.form.get(
            "payment_method",
            "Cash"
        )

        customer = conn.execute("""
            SELECT id
            FROM customers
            WHERE room = ?
            ORDER BY id DESC
            LIMIT 1
        """, (room,)).fetchone()

        if not customer:

            payment_data = conn.execute("""
                SELECT *
                FROM customers
                WHERE payment_status = 'Paid'
                ORDER BY id DESC
            """).fetchall()

            conn.close()

            return render_template(
                "payments.html",
                payments=payment_data,
                error=f"No customer found for Room {room}."
            )

        # -------------------------------------------------
        # SAVE PAYMENT
        # -------------------------------------------------

        conn.execute("""
            UPDATE customers
            SET
                payment_method = ?,
                payment_status = 'Paid'
            WHERE id = ?
        """, (
            payment_method,
            customer["id"]
        ))

        conn.commit()

        payment_data = conn.execute("""
            SELECT *
            FROM customers
            WHERE payment_status = 'Paid'
            ORDER BY id DESC
        """).fetchall()

        conn.close()

        return render_template(
            "payments.html",
            payments=payment_data,
            success=f"Payment saved for Room {room}."
        )

    # -----------------------------------------------------
    # DISPLAY PAYMENTS
    # -----------------------------------------------------

    payment_data = conn.execute("""
        SELECT *
        FROM customers
        WHERE payment_status = 'Paid'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "payments.html",
        payments=payment_data
    )


# =========================================================
# 404 ERROR
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return """
    <!DOCTYPE html>
    <html>

    <head>
        <title>404 - Page Not Found</title>

        <style>

            body {
                font-family: Arial;
                text-align: center;
                padding: 50px;
            }

            a {
                text-decoration: none;
                background: #333;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
            }

        </style>

    </head>

    <body>

        <h1>404 - Page Not Found</h1>

        <p>The page you are looking for does not exist.</p>

        <br>

        <a href="/">
            Back to Dashboard
        </a>

    </body>

    </html>
    """, 404


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )