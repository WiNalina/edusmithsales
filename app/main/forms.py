from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    IntegerField,
    FloatField,
    BooleanField,
    TextAreaField,
    SelectField,
    SubmitField,
)
from wtforms.fields.html5 import DateField, DateTimeLocalField, DateTimeField, TimeField
from wtforms.validators import NumberRange, DataRequired, Length
from flask_babel import _, lazy_gettext as _l
from flask import request
import datetime
import pytz


def number_of_days(y, m):
    leap = 0
    if y % 400 == 0:
        leap = 1
    elif y % 100 == 0:
        leap = 0
    elif y % 4 == 0:
        leap = 1
    if m == 2:
        return 28 + leap
    list = [1, 3, 5, 7, 8, 10, 12]
    if m in list:
        return 31
    return 30


class TransactionForm(FlaskForm):
    # Set up a transaction form

    # Student Info
    student_full_name = StringField(
        "Student Full Name",
        validators=[DataRequired()],
        render_kw={"placeholder": "Please Enter The Student's Name"},
    )
    use_company_info_flag = BooleanField("Use Company Information")
    client_company_name = StringField("Client - Company Name")
    client_address = StringField("Client - Address")
    client_tax_id = StringField("Client - Tax ID")

    # Service Section
    # Each service has name, price, discount value, count, final price (price * count - discount value), and note
    # Service 1 Information
    service_1_name = StringField(
        "Service 1: Name",
        validators=[DataRequired()],
        id="service_1_name",
        render_kw={"placeholder": "Please Enter The 1st Service Name"},
    )
    service_1_price = FloatField("Service 1: Price", validators=[DataRequired()])
    service_1_discount_value = FloatField(
        "Service 1: Discount Value",
        default=0.0,
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
    )
    service_1_count = FloatField(
        "Service 1: Count",
        validators=[
            DataRequired(),
            NumberRange(min=0, message="Please enter 0 or a positive value"),
        ],
        default=0.0,
    )
    service_1_final_price = FloatField("Service 1: Final Price", default=0.0)
    service_1_note = StringField("Service 1: Note")
    service_1_teacher_name = StringField("Service 1: Teacher")
    service_1_office = SelectField(
        "Service 1: Office",
        choices=[
            ("Asok", "Asok"),
            ("Nichada", "Nichada"),
            ("MBK", "MBK"),
            ("Online", "Online"),
        ],
    )

    service_1_refund_flag = BooleanField("Service 1: Refund Flag")
    service_1_refund_status = SelectField(
        "Service 1: Refund Status",
        choices=[
            ("None", "None"),
            ("Partial", "Partial"),
            ("Full", "Full"),
            ("Credit", "Credit"),
            ("Turned into credit for another BU", "Turned into credit for another BU"),
        ],
    )
    service_1_credit_note_number = StringField("Service 1: Credit Note Number")
    service_1_refund_amount = FloatField("Service 1: Refund Amount", default=0.0)
    service_1_refund_date = DateField(
        "Service 1: Refund Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )

    service_1_amortization_type = SelectField(
        "Service 1: Amortization Rule", validate_choice=False
    )
    service_1_start_date = DateField(
        "Service 1: Start Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone
    service_1_end_date = DateField(
        "Service 1: End Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone

    service_1_total_hours = FloatField("Service 1: Total Number of Hours", default=0.0)
    service_1_monday_hours = FloatField("Service 1: Monday Hours", default=0.0)
    service_1_tuesday_hours = FloatField("Service 1: Tuesday Hours", default=0.0)
    service_1_wednesday_hours = FloatField("Service 1: Wednesday Hours", default=0.0)
    service_1_thursday_hours = FloatField("Service 1: Thursday Hours", default=0.0)
    service_1_friday_hours = FloatField("Service 1: Friday Hours", default=0.0)
    service_1_saturday_hours = FloatField("Service 1: Saturday Hours", default=0.0)
    service_1_sunday_hours = FloatField("Service 1: Sunday Hours", default=0.0)

    service_1_month_1_hrs = FloatField("Service 1: Month 1 Hrs", default=0.0)
    service_1_month_2_hrs = FloatField("Service 1: Month 2 Hrs", default=0.0)
    service_1_month_3_hrs = FloatField("Service 1: Month 3 Hrs", default=0.0)
    service_1_month_4_hrs = FloatField("Service 1: Month 4 Hrs", default=0.0)
    service_1_month_5_hrs = FloatField("Service 1: Month 5 Hrs", default=0.0)
    service_1_month_6_hrs = FloatField("Service 1: Month 6 Hrs", default=0.0)

    # Service 2
    service_2_name = StringField(
        "Service 2: Name",
        render_kw={"placeholder": "Please Enter The 2nd Service Name"},
    )
    service_2_price = FloatField("Service 2: Price", default=0.0)
    service_2_discount_value = FloatField(
        "Service 2: Discount Value",
        default=0.0,
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
    )
    service_2_count = FloatField(
        "Service 2: Count",
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
        default=0.0,
    )
    service_2_final_price = FloatField("Service 2: Final Price", default=0.0)
    service_2_note = StringField("Service 2: Note")
    service_2_teacher_name = StringField("Service 2: Teacher")
    service_2_office = SelectField(
        "Service 2: Office",
        choices=[
            ("Asok", "Asok"),
            ("Nichada", "Nichada"),
            ("MBK", "MBK"),
            ("Online", "Online"),
        ],
    )

    service_2_refund_flag = BooleanField("Service 2: Refund Flag")
    service_2_refund_status = SelectField(
        "Service 2: Refund Status",
        choices=[
            ("None", "None"),
            ("Partial", "Partial"),
            ("Full", "Full"),
            ("Credit", "Credit"),
            ("Turned into credit for another BU", "Turned into credit for another BU"),
        ],
    )
    service_2_credit_note_number = StringField("Service 2: Credit Note Number")
    service_2_refund_amount = FloatField("Service 2: Refund Amount", default=0.0)
    service_2_refund_date = DateField(
        "Service 2: Refund Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )

    service_2_amortization_type = SelectField(
        "Service 2: Amortization Rule", validate_choice=False
    )
    service_2_start_date = DateField(
        "Service 2: Start Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone
    service_2_end_date = DateField(
        "Service 2: End Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone

    service_2_total_hours = FloatField("Service 2: Total Number of Hours", default=0.0)
    service_2_monday_hours = FloatField("Service 2: Monday Hours", default=0.0)
    service_2_tuesday_hours = FloatField("Service 2: Tuesday Hours", default=0.0)
    service_2_wednesday_hours = FloatField("Service 2: Wednesday Hours", default=0.0)
    service_2_thursday_hours = FloatField("Service 2: Thursday Hours", default=0.0)
    service_2_friday_hours = FloatField("Service 2: Friday Hours", default=0.0)
    service_2_saturday_hours = FloatField("Service 2: Saturday Hours", default=0.0)
    service_2_sunday_hours = FloatField("Service 2: Sunday Hours", default=0.0)

    service_2_month_1_hrs = FloatField("Service 2: Month 1 Hrs", default=0.0)
    service_2_month_2_hrs = FloatField("Service 2: Month 2 Hrs", default=0.0)
    service_2_month_3_hrs = FloatField("Service 2: Month 3 Hrs", default=0.0)
    service_2_month_4_hrs = FloatField("Service 2: Month 4 Hrs", default=0.0)
    service_2_month_5_hrs = FloatField("Service 2: Month 5 Hrs", default=0.0)
    service_2_month_6_hrs = FloatField("Service 2: Month 6 Hrs", default=0.0)

    # Service 3
    service_3_name = StringField(
        "Service 3: Name",
        render_kw={"placeholder": "Please Enter The 3rd Service Name"},
    )
    service_3_price = FloatField("Service 3: Price", default=0.0)
    service_3_discount_value = FloatField(
        "Service 3: Discount Value",
        default=0.0,
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
    )
    service_3_count = FloatField(
        "Service 3: Count",
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
        default=0.0,
    )
    service_3_final_price = FloatField("Service 3: Final Price", default=0.0)
    service_3_note = StringField("Service 3: Note")
    service_3_teacher_name = StringField("Service 3: Teacher")
    service_3_office = SelectField(
        "Service 3: Office",
        choices=[
            ("Asok", "Asok"),
            ("Nichada", "Nichada"),
            ("MBK", "MBK"),
            ("Online", "Online"),
        ],
    )

    service_3_refund_flag = BooleanField("Service 3: Refund Flag")
    service_3_refund_status = SelectField(
        "Service 3: Refund Status",
        choices=[
            ("None", "None"),
            ("Partial", "Partial"),
            ("Full", "Full"),
            ("Credit", "Credit"),
            ("Turned into credit for another BU", "Turned into credit for another BU"),
        ],
    )
    service_3_credit_note_number = StringField("Service 3: Credit Note Number")
    service_3_refund_amount = FloatField("Service 3: Refund Amount", default=0.0)
    service_3_refund_date = DateField(
        "Service 3: Refund Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )

    service_3_amortization_type = SelectField(
        "Service 3: Amortization Rule", validate_choice=False
    )
    service_3_start_date = DateField(
        "Service 3: Start Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone
    service_3_end_date = DateField(
        "Service 3: End Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone

    service_3_total_hours = FloatField("Service 3: Total Number of Hours", default=0.0)
    service_3_monday_hours = FloatField("Service 3: Monday Hours", default=0.0)
    service_3_tuesday_hours = FloatField("Service 3: Tuesday Hours", default=0.0)
    service_3_wednesday_hours = FloatField("Service 3: Wednesday Hours", default=0.0)
    service_3_thursday_hours = FloatField("Service 3: Thursday Hours", default=0.0)
    service_3_friday_hours = FloatField("Service 3: Friday Hours", default=0.0)
    service_3_saturday_hours = FloatField("Service 3: Saturday Hours", default=0.0)
    service_3_sunday_hours = FloatField("Service 3: Sunday Hours", default=0.0)

    service_3_month_1_hrs = FloatField("Service 3: Month 1 Hrs", default=0.0)
    service_3_month_2_hrs = FloatField("Service 3: Month 2 Hrs", default=0.0)
    service_3_month_3_hrs = FloatField("Service 3: Month 3 Hrs", default=0.0)
    service_3_month_4_hrs = FloatField("Service 3: Month 4 Hrs", default=0.0)
    service_3_month_5_hrs = FloatField("Service 3: Month 5 Hrs", default=0.0)
    service_3_month_6_hrs = FloatField("Service 3: Month 6 Hrs", default=0.0)

    # Service 4
    service_4_name = StringField(
        "Service 4: Name",
        render_kw={"placeholder": "Please Enter The 4th Service Name"},
    )
    service_4_price = FloatField("Service 4: Price", default=0.0)
    service_4_discount_value = FloatField(
        "Service 4: Discount Value",
        default=0.0,
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
    )
    service_4_count = FloatField(
        "Service 4: Count",
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
        default=0.0,
    )
    service_4_final_price = FloatField("Service 4: Final Price", default=0.0)
    service_4_note = StringField("Service 4: Note")
    service_4_teacher_name = StringField("Service 4: Teacher")
    service_4_office = SelectField(
        "Service 4: Office",
        choices=[
            ("Asok", "Asok"),
            ("Nichada", "Nichada"),
            ("MBK", "MBK"),
            ("Online", "Online"),
        ],
    )

    service_4_refund_flag = BooleanField("Service 4: Refund Flag")
    service_4_refund_status = SelectField(
        "Service 4: Refund Status",
        choices=[
            ("None", "None"),
            ("Partial", "Partial"),
            ("Full", "Full"),
            ("Credit", "Credit"),
            ("Turned into credit for another BU", "Turned into credit for another BU"),
        ],
    )
    service_4_credit_note_number = StringField("Service 4: Credit Note Number")
    service_4_refund_amount = FloatField("Service 4: Refund Amount", default=0.0)
    service_4_refund_date = DateField(
        "Service 4: Refund Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )

    service_4_amortization_type = SelectField(
        "Service 4: Amortization Rule", validate_choice=False
    )
    service_4_start_date = DateField(
        "Service 4: Start Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone
    service_4_end_date = DateField(
        "Service 4: End Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone

    service_4_total_hours = FloatField("Service 4: Total Number of Hours", default=0.0)
    service_4_monday_hours = FloatField("Service 4: Monday Hours", default=0.0)
    service_4_tuesday_hours = FloatField("Service 4: Tuesday Hours", default=0.0)
    service_4_wednesday_hours = FloatField("Service 4: Wednesday Hours", default=0.0)
    service_4_thursday_hours = FloatField("Service 4: Thursday Hours", default=0.0)
    service_4_friday_hours = FloatField("Service 4: Friday Hours", default=0.0)
    service_4_saturday_hours = FloatField("Service 4: Saturday Hours", default=0.0)
    service_4_sunday_hours = FloatField("Service 4: Sunday Hours", default=0.0)

    service_4_month_1_hrs = FloatField("Service 4: Month 1 Hrs", default=0.0)
    service_4_month_2_hrs = FloatField("Service 4: Month 2 Hrs", default=0.0)
    service_4_month_3_hrs = FloatField("Service 4: Month 3 Hrs", default=0.0)
    service_4_month_4_hrs = FloatField("Service 4: Month 4 Hrs", default=0.0)
    service_4_month_5_hrs = FloatField("Service 4: Month 5 Hrs", default=0.0)
    service_4_month_6_hrs = FloatField("Service 4: Month 6 Hrs", default=0.0)

    # Service 5
    service_5_name = StringField(
        "Service 5: Name",
        render_kw={"placeholder": "Please Enter The 5th Service Name"},
    )
    service_5_price = FloatField("Service 5: Price", default=0.0)
    service_5_discount_value = FloatField(
        "Service 5: Discount Value",
        default=0.0,
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
    )
    service_5_count = FloatField(
        "Service 5: Count",
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
        default=0.0,
    )
    service_5_final_price = FloatField("Service 5: Final Price", default=0.0)
    service_5_note = StringField("Service 5: Note")
    service_5_teacher_name = StringField("Service 5: Teacher")
    service_5_office = SelectField(
        "Service 5: Office",
        choices=[
            ("Asok", "Asok"),
            ("Nichada", "Nichada"),
            ("MBK", "MBK"),
            ("Online", "Online"),
        ],
    )

    service_5_refund_flag = BooleanField("Service 5: Refund Flag")
    service_5_refund_status = SelectField(
        "Service 5: Refund Status",
        choices=[
            ("None", "None"),
            ("Partial", "Partial"),
            ("Full", "Full"),
            ("Credit", "Credit"),
            ("Turned into credit for another BU", "Turned into credit for another BU"),
        ],
    )
    service_5_credit_note_number = StringField("Service 5: Credit Note Number")
    service_5_refund_amount = FloatField("Service 5: Refund Amount", default=0.0)
    service_5_refund_date = DateField(
        "Service 5: Refund Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )

    service_5_amortization_type = SelectField(
        "Service 5: Amortization Rule", validate_choice=False
    )
    service_5_start_date = DateField(
        "Service 5: Start Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone
    service_5_end_date = DateField(
        "Service 5: End Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone

    service_5_total_hours = FloatField("Service 5: Total Number of Hours", default=0.0)
    service_5_monday_hours = FloatField("Service 5: Monday Hours", default=0.0)
    service_5_tuesday_hours = FloatField("Service 5: Tuesday Hours", default=0.0)
    service_5_wednesday_hours = FloatField("Service 5: Wednesday Hours", default=0.0)
    service_5_thursday_hours = FloatField("Service 5: Thursday Hours", default=0.0)
    service_5_friday_hours = FloatField("Service 5: Friday Hours", default=0.0)
    service_5_saturday_hours = FloatField("Service 5: Saturday Hours", default=0.0)
    service_5_sunday_hours = FloatField("Service 5: Sunday Hours", default=0.0)

    service_5_month_1_hrs = FloatField("Service 5: Month 1 Hrs", default=0.0)
    service_5_month_2_hrs = FloatField("Service 5: Month 2 Hrs", default=0.0)
    service_5_month_3_hrs = FloatField("Service 5: Month 3 Hrs", default=0.0)
    service_5_month_4_hrs = FloatField("Service 5: Month 4 Hrs", default=0.0)
    service_5_month_5_hrs = FloatField("Service 5: Month 5 Hrs", default=0.0)
    service_5_month_6_hrs = FloatField("Service 5: Month 6 Hrs", default=0.0)

    # Service 6
    service_6_name = StringField(
        "Service 6: Name",
        render_kw={"placeholder": "Please Enter The 6th Service Name"},
    )
    service_6_price = FloatField("Service 6: Price", default=0)
    service_6_discount_value = FloatField(
        "Service 6: Discount Value",
        default=0.0,
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
    )
    service_6_count = FloatField(
        "Service 6: Count",
        validators=[
            NumberRange(
                min=0, message="Please enter 0 or a positive value before proceeding"
            )
        ],
        default=0.0,
    )
    service_6_final_price = FloatField("Service 6: Final Price", default=0)
    service_6_note = StringField("Service 6: Note")
    service_6_teacher_name = StringField("Service 6: Teacher")
    service_6_office = SelectField(
        "Service 6: Office",
        choices=[
            ("Asok", "Asok"),
            ("Nichada", "Nichada"),
            ("MBK", "MBK"),
            ("Online", "Online"),
        ],
    )

    service_6_refund_flag = BooleanField("Service 6: Refund Flag")
    service_6_refund_status = SelectField(
        "Service 6: Refund Status",
        choices=[
            ("None", "None"),
            ("Partial", "Partial"),
            ("Full", "Full"),
            ("Credit", "Credit"),
            ("Turned into credit for another BU", "Turned into credit for another BU"),
        ],
    )
    service_6_credit_note_number = StringField("Service 6: Credit Note Number")
    service_6_refund_amount = FloatField("Service 6: Refund Amount", default=0.0)
    service_6_refund_date = DateField(
        "Service 6: Refund Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )

    service_6_amortization_type = SelectField(
        "Service 6: Amortization Rule", validate_choice=False
    )
    service_6_start_date = DateField(
        "Service 6: Start Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone
    service_6_end_date = DateField(
        "Service 6: End Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone

    service_6_total_hours = FloatField("Service 6: Total Number of Hours", default=0.0)
    service_6_monday_hours = FloatField("Service 6: Monday Hours", default=0.0)
    service_6_tuesday_hours = FloatField("Service 6: Tuesday Hours", default=0.0)
    service_6_wednesday_hours = FloatField("Service 6: Wednesday Hours", default=0.0)
    service_6_thursday_hours = FloatField("Service 6: Thursday Hours", default=0.0)
    service_6_friday_hours = FloatField("Service 6: Friday Hours", default=0.0)
    service_6_saturday_hours = FloatField("Service 6: Saturday Hours", default=0.0)
    service_6_sunday_hours = FloatField("Service 6: Sunday Hours", default=0.0)

    service_6_month_1_hrs = FloatField("Service 6: Month 1 Hrs", default=0.0)
    service_6_month_2_hrs = FloatField("Service 6: Month 2 Hrs", default=0.0)
    service_6_month_3_hrs = FloatField("Service 6: Month 3 Hrs", default=0.0)
    service_6_month_4_hrs = FloatField("Service 6: Month 4 Hrs", default=0.0)
    service_6_month_5_hrs = FloatField("Service 6: Month 5 Hrs", default=0.0)
    service_6_month_6_hrs = FloatField("Service 6: Month 6 Hrs", default=0.0)

    # Overall Information
    # Overall discount that applies to all of the services
    overall_discount = FloatField("Overall Discount", default=0.0)
    # The sum of all final prices for all of the services
    total_value = FloatField(
        "Total Value",
        validators=[NumberRange(min=0, message="Please enter 0 or a positive value")],
    )

    # Due Date Part
    # Set the payment due date with the default value being the next 7 days
    next_7_day_date = datetime.datetime.now() + datetime.timedelta(days=7)
    due_date = DateField("Payment Due Date", format="%Y-%m-%d", default=next_7_day_date)
    # Payment Method - Used for generating a receipt
    payment_method = SelectField(
        "Payment Method",
        choices=["Unknown", "Cash", "Bank Transfer", "Credit Card", "Debit Card"],
    )
    card_machine = SelectField("Credit/Debit Card Machine", validate_choice=False)
    card_issuer = SelectField(
        "Card Issuer", choices=["None", "Thai Bank", "International Bank"]
    )
    payment_date = DateField("Payment Date", default=datetime.datetime.now())

    tz = pytz.timezone("Asia/Bangkok")  # timezone you want to convert to from UTC
    utc = pytz.timezone("UTC")
    value = utc.localize(datetime.datetime.utcnow(), is_dst=None).astimezone(pytz.utc)
    local_dt = value.astimezone(tz)
    payment_time = TimeField("Payment Time", default=local_dt)

    this_time_payment = FloatField(
        "Non-credit Payment",
        validators=[NumberRange(min=0, message="Please enter 0 or a positive value")],
        default=0.0,
    )
    use_credit_flag = BooleanField("Use Credit")
    credit_outstanding = FloatField(
        "Credit Outstanding",
        validators=[NumberRange(min=0, message="Please enter 0 or a positive value")],
        default=0.0,
    )
    credit_spending_amount = FloatField(
        "Credit Spending Amount",
        validators=[NumberRange(min=0, message="Please enter 0 or a positive value")],
        default=0.0,
    )
    remaining_outstanding = FloatField(
        "Remaining Outstanding",
        validators=[NumberRange(min=0, message="Please enter 0 or a positive value")],
        default=0.0,
    )
    # Document Generation
    generate_invoice_flag = BooleanField("Invoice")
    generate_receipt_flag = BooleanField("Receipt")
    # Add three cases of transaction changes
    refund_flag = BooleanField("Refund")
    cancel_flag = BooleanField("Transaction Cancelled")
    complete_flag = BooleanField("Completed")
    # Refund Amount
    refund_amount = FloatField(
        "Refund Amount",
        default=0.0,
        validators=[NumberRange(min=0, message="Please enter 0 or a positive value")],
        render_kw={"placeholder": "Enter The Refund Amount"},
    )
    # Note
    note = TextAreaField("Note", validators=[Length(min=0, max=400)])
    # Submit & Preview
    submit = SubmitField("Submit")
    preview = SubmitField("Preview")

    def validate(self):
        if not super(TransactionForm, self).validate():
            return False

        if self.generate_receipt_flag.data:
            if (
                self.payment_method.data == "Credit Card"
                or self.payment_method.data == "Debit Card"
            ):
                if self.card_machine.data == "Unknown":
                    msg = "Please enter the card information in the card machine field."
                    self.card_machine.errors.append(msg)
                    return False
                if self.card_issuer.data == "None":
                    msg = "Please enter the card issuer in the card issuer field."
                    self.card_issuer.errors.append(msg)
                    return False

        # Invoice & Receipt

        if (
            self.generate_invoice_flag.data
            and self.this_time_payment.data == 0
            and self.this_time_payment.data == 0.0
            and self.credit_spending_amount.data == 0.0
        ):
            msg = (
                "To generate an invoice, please enter the payment for this transaction"
            )
            self.this_time_payment.errors.append(msg)
            return False
        if (
            self.generate_receipt_flag.data
            and self.payment_method.data == "Unknown"
            and self.this_time_payment.data > 0.0
        ):
            msg = "To generate a receipt, please choose a specific payment method"
            self.payment_method.errors.append(msg)
            return False

        # Amortization Part

        if self.service_1_amortization_type.data == "Constant":
            if self.service_1_start_date.data > self.service_1_end_date.data:
                msg = "The end date must be after the start date"
                self.service_1_start_date.errors.append(msg)
                self.service_1_end_date.errors.append(msg)
                return False
        elif self.service_1_amortization_type.data == "Fixed Hrs/Week":
            sum_hrs = (
                self.service_1_monday_hours.data
                + self.service_1_tuesday_hours.data
                + self.service_1_wednesday_hours.data
                + self.service_1_thursday_hours.data
                + self.service_1_friday_hours.data
                + self.service_1_saturday_hours.data
                + self.service_1_sunday_hours.data
            )
            if sum_hrs > self.service_1_total_hours.data:
                msg = "The total number of hours exceed the sum of hours for all days"
                self.service_1_total_hours.errors.append(msg)
                return False
            if sum_hrs == 0 or self.service_1_total_hours.data == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_1_total_hours.errors.append(msg)
                return False
        elif self.service_1_amortization_type.data == "Custom":
            sum_hrs = (
                self.service_1_month_1_hrs.data
                + self.service_1_month_2_hrs.data
                + self.service_1_month_3_hrs.data
                + self.service_1_month_4_hrs.data
                + self.service_1_month_5_hrs.data
                + self.service_1_month_6_hrs.data
            )
            if sum_hrs == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_1_amortization_type.errors.append(msg)
                return False

        if self.service_2_amortization_type.data == "Constant":
            if self.service_2_start_date.data > self.service_2_end_date.data:
                msg = "The end date must be after the start date"
                self.service_2_start_date.errors.append(msg)
                self.service_2_end_date.errors.append(msg)
                return False
        elif self.service_2_amortization_type.data == "Fixed Hrs/Week":
            sum_hrs = (
                self.service_2_monday_hours.data
                + self.service_2_tuesday_hours.data
                + self.service_2_wednesday_hours.data
                + self.service_2_thursday_hours.data
                + self.service_2_friday_hours.data
                + self.service_2_saturday_hours.data
                + self.service_2_sunday_hours.data
            )
            if sum_hrs > self.service_2_total_hours.data:
                msg = "The total number of hours exceed the sum of hours for all days"
                self.service_2_total_hours.errors.append(msg)
                return False
            if sum_hrs == 0 or self.service_2_total_hours.data == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_2_total_hours.errors.append(msg)
                return False
        elif self.service_2_amortization_type.data == "Custom":
            sum_hrs = (
                self.service_2_month_1_hrs.data
                + self.service_2_month_2_hrs.data
                + self.service_2_month_3_hrs.data
                + self.service_2_month_4_hrs.data
                + self.service_2_month_5_hrs.data
                + self.service_2_month_6_hrs.data
            )
            if sum_hrs == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_2_amortization_type.errors.append(msg)
                return False

        if self.service_3_amortization_type.data == "Constant":
            if self.service_3_start_date.data > self.service_3_end_date.data:
                msg = "The end date must be after the start date"
                self.service_3_start_date.errors.append(msg)
                self.service_3_end_date.errors.append(msg)
                return False
        elif self.service_3_amortization_type.data == "Fixed Hrs/Week":
            sum_hrs = (
                self.service_3_monday_hours.data
                + self.service_3_tuesday_hours.data
                + self.service_3_wednesday_hours.data
                + self.service_3_thursday_hours.data
                + self.service_3_friday_hours.data
                + self.service_3_saturday_hours.data
                + self.service_3_sunday_hours.data
            )
            if sum_hrs > self.service_3_total_hours.data:
                msg = "The total number of hours exceed the sum of hours for all days"
                self.service_3_total_hours.errors.append(msg)
                return False
            if sum_hrs == 0 or self.service_3_total_hours.data == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_3_total_hours.errors.append(msg)
                return False
        elif self.service_3_amortization_type.data == "Custom":
            sum_hrs = (
                self.service_3_month_1_hrs.data
                + self.service_3_month_2_hrs.data
                + self.service_3_month_3_hrs.data
                + self.service_3_month_4_hrs.data
                + self.service_3_month_5_hrs.data
                + self.service_3_month_6_hrs.data
            )
            if sum_hrs == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_3_amortization_type.errors.append(msg)
                return False

        if self.service_4_amortization_type.data == "Constant":
            if self.service_4_start_date.data > self.service_4_end_date.data:
                msg = "The end date must be after the start date"
                self.service_4_start_date.errors.append(msg)
                self.service_4_end_date.errors.append(msg)
                return False
        elif self.service_4_amortization_type.data == "Fixed Hrs/Week":
            sum_hrs = (
                self.service_4_monday_hours.data
                + self.service_4_tuesday_hours.data
                + self.service_4_wednesday_hours.data
                + self.service_4_thursday_hours.data
                + self.service_4_friday_hours.data
                + self.service_4_saturday_hours.data
                + self.service_4_sunday_hours.data
            )
            if sum_hrs > self.service_4_total_hours.data:
                msg = "The total number of hours exceed the sum of hours for all days"
                self.service_4_total_hours.errors.append(msg)
                return False
            if sum_hrs == 0 or self.service_4_total_hours.data == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_4_total_hours.errors.append(msg)
                return False
        elif self.service_4_amortization_type.data == "Custom":
            sum_hrs = (
                self.service_4_month_1_hrs.data
                + self.service_4_month_2_hrs.data
                + self.service_4_month_3_hrs.data
                + self.service_4_month_4_hrs.data
                + self.service_4_month_5_hrs.data
                + self.service_4_month_6_hrs.data
            )
            if sum_hrs == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_4_amortization_type.errors.append(msg)
                return False

        if self.service_5_amortization_type.data == "Constant":
            if self.service_5_start_date.data > self.service_5_end_date.data:
                msg = "The end date must be after the start date"
                self.service_5_start_date.errors.append(msg)
                self.service_5_end_date.errors.append(msg)
                return False
        elif self.service_5_amortization_type.data == "Fixed Hrs/Week":
            sum_hrs = (
                self.service_5_monday_hours.data
                + self.service_5_tuesday_hours.data
                + self.service_5_wednesday_hours.data
                + self.service_5_thursday_hours.data
                + self.service_5_friday_hours.data
                + self.service_5_saturday_hours.data
                + self.service_5_sunday_hours.data
            )
            if sum_hrs > self.service_5_total_hours.data:
                msg = "The total number of hours exceed the sum of hours for all days"
                self.service_5_total_hours.errors.append(msg)
                return False
            if sum_hrs == 0 or self.service_5_total_hours.data == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_5_total_hours.errors.append(msg)
                return False
        elif self.service_5_amortization_type.data == "Custom":
            sum_hrs = (
                self.service_5_month_1_hrs.data
                + self.service_5_month_2_hrs.data
                + self.service_5_month_3_hrs.data
                + self.service_5_month_4_hrs.data
                + self.service_5_month_5_hrs.data
                + self.service_5_month_6_hrs.data
            )
            if sum_hrs == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_5_amortization_type.errors.append(msg)
                return False

        if self.service_6_amortization_type.data == "Constant":
            if self.service_6_start_date.data > self.service_6_end_date.data:
                msg = "The end date must be after the start date"
                self.service_6_start_date.errors.append(msg)
                self.service_6_end_date.errors.append(msg)
                return False
        elif self.service_6_amortization_type.data == "Fixed Hrs/Week":
            sum_hrs = (
                self.service_6_monday_hours.data
                + self.service_6_tuesday_hours.data
                + self.service_6_wednesday_hours.data
                + self.service_6_thursday_hours.data
                + self.service_6_friday_hours.data
                + self.service_6_saturday_hours.data
                + self.service_6_sunday_hours.data
            )
            if sum_hrs > self.service_6_total_hours.data:
                msg = "The total number of hours exceed the sum of hours for all days"
                self.service_6_total_hours.errors.append(msg)
                return False
            if sum_hrs == 0 or self.service_6_total_hours.data == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_6_total_hours.errors.append(msg)
                return False
        elif self.service_6_amortization_type.data == "Custom":
            sum_hrs = (
                self.service_6_month_1_hrs.data
                + self.service_6_month_2_hrs.data
                + self.service_6_month_3_hrs.data
                + self.service_6_month_4_hrs.data
                + self.service_6_month_5_hrs.data
                + self.service_6_month_6_hrs.data
            )
            if sum_hrs == 0:
                msg = "The total number of hours must be greater than 0"
                self.service_6_amortization_type.errors.append(msg)
                return False

        if self.credit_spending_amount.data > self.credit_outstanding.data:
            msg = "The credit spending amount exceeds the credit outstanding"
            self.credit_spending_amount.errors.append(msg)
            return False

        return True


class EmptyForm(FlaskForm):
    # Empty form having only the submit button
    submit = SubmitField("Submit")


class ServiceForm_lookup(FlaskForm):
    # Lookup form for finding services
    # Form for finding the services
    name = StringField(
        "Service Name",
        validators=[DataRequired()],
        render_kw={"placeholder": "Please Enter The Service Name"},
    )
    submit = SubmitField("Submit")


class ServiceForm_global(FlaskForm):
    # The form for editing or adding services
    # Service Category
    category = SelectField(
        "Service Category",
        choices=[
            ["None", "None"],
            ("Coaching", "Coaching"),
            ("Counseling", "Counseling"),
            ("Group course", "Group course"),
            ("Private", "Private"),
            ("APPA", "APPA"),
        ],
    )
    # Service Subcategory
    subcategory = SelectField("Service Subcategory", validate_choice=False)
    # Service Name
    name = StringField("Service Standard Name ", validators=[DataRequired()])
    # Service Non-VAT Name
    non_vat_name = StringField(
        "Service Non-VAT Name (For display in receipts/accounting records)"
    )
    non_vat_same_as_name_flag = BooleanField("Same as service standard name")
    # Service VAT Name
    vat_name = StringField("Service VAT Name (For VAT receipt)")
    vat_same_as_name_flag = BooleanField("Same as service standard name")
    # Service Display Name
    display_name = StringField("Service Display Name")
    # Service Country
    country = SelectField("Service Country", choices=["Thailand", "Myanmar"])
    # VAT proportion for each service
    vat_proportion = FloatField("VAT Proportion", default=0.0)
    # Service price
    price = FloatField("Price", validators=[DataRequired()])
    submit = SubmitField("Submit")


class StudentForm_lookup(FlaskForm):
    # The form for looking up for students
    # Student name
    name = StringField(
        "Student Name",
        validators=[DataRequired()],
        render_kw={"placeholder": "Please Enter The Student Name"},
    )
    submit = SubmitField("Submit")


class Document_lookup(FlaskForm):
    # The form for looking up accounting records
    # Starting month and year for querying accounting records
    current_day = datetime.datetime.utcnow()

    month_start_datetime = datetime.datetime(
        day=1, month=current_day.month, year=current_day.year
    )
    month_end_day = number_of_days(current_day.year, current_day.month)
    month_end_datetime = datetime.datetime(
        minute=current_day.minute,
        hour=current_day.hour,
        day=month_end_day,
        month=current_day.month,
        year=current_day.year,
    )

    start_date_select = DateField(
        "Starting Date", format="%Y-%m-%d", default=month_start_datetime
    )
    end_date_select = DateField(
        "Ending Date", format="%Y-%m-%d", default=month_end_datetime
    )

    # Download button
    submit = SubmitField("Download")


class Amortize_lookup(FlaskForm):
    # The form for looking up accounting records
    # Starting month and year for querying accounting records
    current_day = datetime.datetime.utcnow()

    month_start_datetime = datetime.datetime(
        day=1, month=current_day.month, year=current_day.year
    )
    month_end_day = number_of_days(current_day.year, current_day.month)
    month_end_datetime = datetime.datetime(
        minute=current_day.minute,
        hour=current_day.hour,
        day=month_end_day,
        month=current_day.month,
        year=current_day.year,
    )

    # Amortization Date
    start_date_select = DateField(
        "Starting Date", format="%Y-%m-%d", default=month_start_datetime
    )
    end_date_select = DateField(
        "Ending Date", format="%Y-%m-%d", default=month_end_datetime
    )
    amortize_date_flag = BooleanField(
        "Tick For Amortize Date/Untick For Sales Date", default=True
    )
    submit = SubmitField("Download")


class Sales_lookup(FlaskForm):
    current_day = datetime.datetime.utcnow()
    month_end_day = number_of_days(current_day.year, current_day.month)
    month_end_day = month_end_day
    month_start_day = datetime.datetime(
        day=1, month=current_day.month, year=current_day.year
    )

    start_date_select = DateField(
        "Starting Date", format="%Y-%m-%d", default=month_start_day
    )
    end_date_select = DateField("Ending Date", format="%Y-%m-%d", default=month_end_day)

    # Download button
    submit = SubmitField("Download")


class OfficeForm_lookup(FlaskForm):
    # The form for looking up for offices
    # Office name
    name = StringField(
        "Office Name",
        validators=[DataRequired()],
        render_kw={"placeholder": "Please Enter The Office Information"},
    )
    submit = SubmitField("Submit")


class OfficeForm(FlaskForm):
    name = StringField("Office Name")  # Office name
    country = StringField("Office Country")  # Office country
    info_for_vat = BooleanField(
        "Flag For VAT Information"
    )  # A flag indicating if the indicated information is for VAT
    title = StringField("Document Title")  # Title for referencing to the office
    company_name = StringField("Company Name")  # Company Name
    address_1 = StringField("First Address Line")  # First line of address information
    address_2 = StringField("Second Address Line")  # Second line of address information
    vat_tax_id = StringField(
        "VAT Tax ID"
    )  # VAT tax ID for the office - used for VAT invoice
    email = StringField("Contact Email")  # Contact email for the office
    phone = StringField("Contact Phone Number")  # Contact phone number for the office
    bank_name = StringField("Bank Name")  # Contact bank name for the office
    bank_account_name = StringField("Bank Account Name")  # Bank account name
    bank_account_number = StringField("Bank Account Number")  # Bank account number
    logo_directory = StringField("Logo Directory")  # Logo directory


class TeacherForm_global(FlaskForm):
    # The form for editing or adding services
    # Teacher Name
    name = StringField("Teacher Name", validators=[DataRequired()])
    # Teacher Country
    country = SelectField("Teacher Country", choices=["Thailand", "Myanmar"])
    submit = SubmitField("Submit")


class TeacherForm_lookup(FlaskForm):
    # The form for looking up for students
    # Student name
    name = StringField(
        "Teacher Name",
        validators=[DataRequired()],
        render_kw={"placeholder": "Please Enter The Teacher Name"},
    )
    submit = SubmitField("Submit")


class MachineForm_global(FlaskForm):
    machine_code_number = IntegerField("Code Number", validators=[DataRequired()])
    reference_name = StringField("Reference Name", validators=[DataRequired()])
    bank_name = StringField("Bank Name", validators=[DataRequired()])
    country = SelectField("Machine Country", choices=["Thailand", "Myanmar"])
    submit = SubmitField("Submit")


class MachineForm_lookup(FlaskForm):
    machine_select = SelectField("Credit/Debit Card Machine")
    submit = SubmitField("Submit")


class AmortizeEditForm(FlaskForm):
    amortization_type = SelectField("Amortization Rule", validate_choice=False)
    start_date = DateField(
        "Start Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone
    end_date = DateField(
        "End Date", format="%Y-%m-%d", default=datetime.datetime.utcnow()
    )  # Need to fix the timezone later to be the local Thai time zone rather than the UTC time zone

    total_hours = FloatField("Total Number of Hours", default=0.0)
    monday_hrs = FloatField("Monday Hours", default=0.0)
    tuesday_hrs = FloatField("Tuesday Hours", default=0.0)
    wednesday_hrs = FloatField("Wednesday Hours", default=0.0)
    thursday_hrs = FloatField("Thursday Hours", default=0.0)
    friday_hrs = FloatField("Friday Hours", default=0.0)
    saturday_hrs = FloatField("Saturday Hours", default=0.0)
    sunday_hrs = FloatField("Sunday Hours", default=0.0)

    month_1_hrs = FloatField("Month 1 Hrs", default=0.0)
    month_2_hrs = FloatField("Month 2 Hrs", default=0.0)
    month_3_hrs = FloatField("Month 3 Hrs", default=0.0)
    month_4_hrs = FloatField("Month 4 Hrs", default=0.0)
    month_5_hrs = FloatField("Month 5 Hrs", default=0.0)
    month_6_hrs = FloatField("Month 6 Hrs", default=0.0)

    apply_to_related_records = BooleanField(
        "Apply To All Related Records", default=True
    )

    submit = SubmitField("Submit")


class CreditTransferForm(FlaskForm):
    sender_name = StringField("Sender Name", validators=[DataRequired()])
    sender_outstanding = FloatField("Sender Credit Value")
    transfer_amount = FloatField(
        "Transfer Amount", default=0.0, validators=[DataRequired()]
    )

    recipient_name = StringField("Recipient Name", validators=[DataRequired()])
    recipient_outstanding = FloatField("Recipient Credit Value")

    submit = SubmitField("Submit")

    def validate(self):
        if not super(CreditTransferForm, self).validate():
            return False

        if self.transfer_amount.data > self.sender_outstanding.data:
            msg = "The transfer amount must not exceed the outstanding of the sender"
            self.transfer_amount.errors.append(msg)
            return False

        return True
