import pandas as pd
from pandas import ExcelWriter
import numpy as np
import datetime
import io
import re
import sys
from flask import make_response
from flask_login import current_user

from app import db
from app.models import Service, Accounting_record
from app.main.forms import AmortizeEditForm


def fill_amortization_slots(list_in, amortization_set):
    list_out = [list_in[0]]
    diff_set = amortization_set - {list_in[0]}

    for each_type in diff_set:
        list_out.append(each_type)

    return list_out


def create_former_amortize_list(former_amortize_list, current_amortize_record):
    list_output = list()

    if former_amortize_list is not None:
        former_amortize_list = eval(former_amortize_list)
        for each_list in former_amortize_list:
            assert each_list[1] in {"Constant", "Fixed Hrs/Week", "Custom"}
            temp_dict = dict()
            temp_dict["change_date"] = each_list[0]
            temp_dict["amortize_type"] = each_list[1]
            temp_dict["start_date"] = each_list[2]
            if each_list[1] == "Constant":
                temp_dict["end_date"] = each_list[3]
            elif each_list[1] == "Fixed Hrs/Week":
                temp_dict["num_hrs"] = each_list[3]
                list_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
                for each_ind, each_day in enumerate(list_days):
                    each_day_str = each_day + "_hrs"
                    list_ind = 4 + each_ind
                    temp_dict[each_day_str] = each_list[list_ind]
            else:
                for i in range(1, 7):
                    each_mon_str = "mon_{}_hrs".format(i)
                    list_ind = 3 + i - 1
                    temp_dict[each_mon_str] = each_list[list_ind]

            list_output.append(temp_dict)

    temp_dict = dict()
    temp_dict["amortize_type"] = current_amortize_record.amortization_type
    temp_dict["start_date"] = current_amortize_record.start_date
    if current_amortize_record.amortization_type == "Constant":
        temp_dict["end_date"] = current_amortize_record.end_date

    elif current_amortize_record.amortization_type == "Fixed Hrs/Week":
        temp_dict["num_hrs"] = current_amortize_record.total_hours
        temp_dict["mon_hrs"] = current_amortize_record.monday_hrs
        temp_dict["tue_hrs"] = current_amortize_record.tuesday_hrs
        temp_dict["wed_hrs"] = current_amortize_record.wednesday_hrs
        temp_dict["thu_hrs"] = current_amortize_record.thursday_hrs
        temp_dict["fri_hrs"] = current_amortize_record.friday_hrs
        temp_dict["sat_hrs"] = current_amortize_record.saturday_hrs
        temp_dict["sun_hrs"] = current_amortize_record.sunday_hrs

    else:
        temp_dict["mon_1_hrs"] = current_amortize_record.month_1_hrs
        temp_dict["mon_2_hrs"] = current_amortize_record.month_2_hrs
        temp_dict["mon_3_hrs"] = current_amortize_record.month_3_hrs
        temp_dict["mon_4_hrs"] = current_amortize_record.month_4_hrs
        temp_dict["mon_5_hrs"] = current_amortize_record.month_5_hrs
        temp_dict["mon_6_hrs"] = current_amortize_record.month_6_hrs

    list_output.append(temp_dict)

    return list_output


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


def amortize_by_monthly_hours(dict_info_in, has_change_date, max_num_month=6):
    total_value = dict_info_in["total_value"]
    start_date = dict_info_in["start_date"]
    if has_change_date:
        end_month = dict_info_in["change_date"].month
        end_year = dict_info_in["change_date"].year
    else:
        end_month = None
        end_year = None

    total_hour = 0
    dict_month_year_outstanding_record = dict()
    dict_month_year_hour_record = dict()

    for i in range(1, 7):
        each_mon_hour = dict_info_in["mon_{}_hrs".format(i)]
        total_hour += each_mon_hour

    avg_price_per_hour = total_value / total_hour

    value_outstanding = total_value
    hour_outstanding = total_hour

    temp_date = start_date
    temp_month = temp_date.month
    temp_year = temp_date.year

    for i in range(max_num_month):
        if dict_info_in["mon_{}_hrs".format(i + 1)] > 0:
            if temp_date.year not in dict_month_year_outstanding_record:
                dict_month_year_outstanding_record[temp_date.year] = dict()
            if (
                temp_date.month
                not in dict_month_year_outstanding_record[temp_date.year]
            ):
                dict_month_year_outstanding_record[temp_date.year][temp_date.month] = 0

            if temp_date.year not in dict_month_year_hour_record:
                dict_month_year_hour_record[temp_date.year] = dict()
            if temp_date.month not in dict_month_year_hour_record[temp_date.year]:
                dict_month_year_hour_record[temp_date.year][temp_date.month] = 0

            if has_change_date:
                if end_month == temp_month and end_year == temp_year:
                    temp_num_days = number_of_days(end_year, end_month)
                    temp_proportion = dict_info_in["change_date"].day / temp_num_days

                    temp_hour = (
                        temp_proportion * dict_info_in["mon_{}_hrs".format(i + 1)]
                    )
                    temp_value = avg_price_per_hour * temp_hour
                else:
                    temp_hour = dict_info_in["mon_{}_hrs".format(i + 1)]
                    temp_value = avg_price_per_hour * temp_hour

                dict_month_year_outstanding_record[temp_date.year][
                    temp_date.month
                ] = temp_value
                dict_month_year_hour_record[temp_date.year][temp_date.month] = temp_hour
            else:
                temp_hour = dict_info_in["mon_{}_hrs".format(i + 1)]
                temp_value = avg_price_per_hour * temp_hour
                dict_month_year_outstanding_record[temp_date.year][
                    temp_date.month
                ] = temp_value
                dict_month_year_hour_record[temp_date.year][temp_date.month] = temp_hour

            value_outstanding -= temp_value
            hour_outstanding -= temp_hour

        if temp_month == 12:
            temp_year += 1
            temp_month = 1
        else:
            temp_month += 1

        temp_date = datetime.datetime(day=1, month=temp_month, year=temp_year)

    dict_outstanding = dict()
    dict_outstanding["value"] = value_outstanding
    dict_outstanding["hour"] = hour_outstanding

    return dict_month_year_outstanding_record, dict_outstanding


def amortize_by_constant_rate(dict_info_in, has_change_date):
    total_value = dict_info_in["total_value"]
    start_date = dict_info_in["start_date"]
    end_date = dict_info_in["end_date"]
    if has_change_date:
        change_date = dict_info_in["change_date"]
    timedelta = end_date - start_date
    remaining_days = timedelta.days + 1
    avg_price_per_day = total_value / remaining_days

    dict_month_year_record = dict()
    value_outstanding = total_value

    temp_day = number_of_days(start_date.year, start_date.month)
    temp_end_date = datetime.datetime(
        day=temp_day, month=start_date.month, year=start_date.year
    )
    while remaining_days > 0:
        if temp_end_date.year not in dict_month_year_record:
            dict_month_year_record[temp_end_date.year] = dict()
        if temp_end_date.month not in dict_month_year_record[temp_end_date.year]:
            dict_month_year_record[temp_end_date.year][temp_end_date.month] = 0

        if end_date < temp_end_date:
            if has_change_date and change_date < temp_end_date:
                if (
                    start_date.month == change_date.month
                    and start_date.year == change_date.year
                ):
                    temp_timedelta = end_date - start_date
                    temp_num_days = temp_timedelta.days + 1
                else:
                    temp_num_days = change_date.day
            elif (
                start_date.month == end_date.month and start_date.year == end_date.year
            ):
                temp_timedelta = end_date - start_date
                temp_num_days = temp_timedelta.days + 1
            else:
                temp_num_days = end_date.day
        else:
            if (
                temp_end_date.month == start_date.month
                and temp_end_date.year == start_date.year
            ):
                temp_timedelta = temp_end_date - start_date
                temp_num_days = temp_timedelta.days + 1
            else:
                temp_num_days = number_of_days(temp_end_date.year, temp_end_date.month)

        dict_month_year_record[temp_end_date.year][temp_end_date.month] = (
            temp_num_days * avg_price_per_day
        )
        value_outstanding -= temp_num_days * avg_price_per_day
        remaining_days -= temp_num_days

        if has_change_date and change_date < temp_end_date:
            break

        if temp_end_date.month == 12:
            temp_month = 1
            temp_year = temp_end_date.year + 1
        else:
            temp_month = temp_end_date.month + 1
            temp_year = temp_end_date.year

        temp_day = number_of_days(temp_year, temp_month)
        temp_end_date = datetime.datetime(
            day=temp_day, month=temp_month, year=temp_year
        )

    dict_outstanding = dict()
    dict_outstanding["value"] = value_outstanding

    return dict_month_year_record, dict_outstanding


def create_weekly_dict(list_in):
    dict_output = dict()
    temp_list = list()

    for i in range(len(list_in)):
        if list_in[i] > 0:
            temp_list.append(i)

    if len(temp_list) == 7:
        for i in range(len(temp_list)):
            dict_output[i] = 1
    else:
        for i in range(len(temp_list)):
            if i == len(temp_list) - 1:
                day_diff = temp_list[0] + 7 - temp_list[i]
            else:
                day_diff = temp_list[i + 1] - temp_list[i]

            dict_output[temp_list[i]] = day_diff

    return dict_output


def amortize_by_weekly_hours(dict_info_in, has_change_date):
    total_value = dict_info_in["total_value"]
    total_hours = dict_info_in["num_hrs"]
    if total_hours == 0:
        sys.stderr.write("Total Value: {}".format(total_value))
        sys.stderr.write("Total Hours: {}".format(total_hours))
        sys.stderr.write(str(dict_info_in))
    price_per_hour = float(total_value / total_hours)
    start_date = dict_info_in["start_date"]
    if has_change_date:
        change_date = dict_info_in["change_date"]
    dict_month_year_record = dict()

    value_outstanding = total_value
    hour_outstanding = total_hours

    list_hrs_in_week = list()
    list_str = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    for each_day in list_str:
        list_hrs_in_week.append(dict_info_in[each_day + "_hrs"])

    dict_day_increment = create_weekly_dict(list_hrs_in_week)
    if start_date.weekday() in dict_day_increment:
        temp_date = start_date
    else:
        for i in range(1, 7):
            temp_date = start_date + datetime.timedelta(days=i)
            if temp_date.weekday() in dict_day_increment:
                break

    while total_hours > 0:
        if has_change_date:
            if temp_date >= change_date:
                break

        if list_hrs_in_week[temp_date.weekday()] > 0:
            this_day_hours = list_hrs_in_week[temp_date.weekday()]
            if total_hours < this_day_hours:
                this_day_hours = total_hours

            hour_outstanding -= this_day_hours
            value_outstanding -= this_day_hours * price_per_hour

            if temp_date.year not in dict_month_year_record:
                dict_month_year_record[temp_date.year] = dict()
            if temp_date.month not in dict_month_year_record[temp_date.year]:
                dict_month_year_record[temp_date.year][temp_date.month] = 0

            total_hours -= this_day_hours
            dict_month_year_record[temp_date.year][temp_date.month] += (
                this_day_hours * price_per_hour
            )

        temp_date += datetime.timedelta(days=dict_day_increment[temp_date.weekday()])

    dict_outstanding = dict()
    dict_outstanding["value"] = value_outstanding
    dict_outstanding["hour"] = hour_outstanding

    return dict_month_year_record, dict_outstanding


def process_each_amortize_record(amortize_record):
    former_amortize_list = amortize_record.former_amortization_info
    list_all_amortize = create_former_amortize_list(
        former_amortize_list, amortize_record
    )
    original_total_value = (
        amortize_record.original_price_per_unit * amortize_record.total_service_count
    )

    dict_outstanding = dict()
    dict_outstanding["value"] = original_total_value
    dict_outstanding["num_hrs"] = amortize_record.total_hours

    collect_dict = dict()
    total_output_dict = dict()

    for each_ind, each_amortize_dict in enumerate(list_all_amortize):
        each_amortize_dict["total_value"] = dict_outstanding["value"]
        if "num_hrs" in dict_outstanding:
            each_amortize_dict["num_hrs"] = dict_outstanding["num_hrs"]

        if each_ind + 1 < len(list_all_amortize):
            has_change_date = True
        else:
            has_change_date = False

        if each_amortize_dict["amortize_type"] == "Constant":
            (
                dict_month_year_outstanding_record,
                dict_outstanding,
            ) = amortize_by_constant_rate(each_amortize_dict, has_change_date)
        elif each_amortize_dict["amortize_type"] == "Fixed Hrs/Week":
            (
                dict_month_year_outstanding_record,
                dict_outstanding,
            ) = amortize_by_weekly_hours(each_amortize_dict, has_change_date)
        else:
            (
                dict_month_year_outstanding_record,
                dict_outstanding,
            ) = amortize_by_monthly_hours(each_amortize_dict, has_change_date)

        for each_year in dict_month_year_outstanding_record:
            if each_year not in collect_dict:
                collect_dict[each_year] = dict()

            for each_month in dict_month_year_outstanding_record[each_year]:
                if each_month not in collect_dict[each_year]:
                    collect_dict[each_year][each_month] = 0

                collect_dict[each_year][
                    each_month
                ] += dict_month_year_outstanding_record[each_year][each_month]

    for each_year in collect_dict:
        for each_month in collect_dict[each_year]:
            num_day = number_of_days(each_year, each_month)
            datetime_str = datetime.datetime(
                day=num_day, month=each_month, year=each_year
            ).strftime("%d-%b-%Y")
            total_output_dict[datetime_str] = collect_dict[each_year][each_month]

    return total_output_dict


def populate_amortize_output_dict(
    dict_in, accounting_record_in, amortize_dict_in, list_base_columns, set_base_columns
):
    for each_col in list_base_columns:
        if each_col not in dict_in:
            dict_in[each_col] = list()

        dict_in[each_col].append(getattr(accounting_record_in, each_col))

    len_in_dict = len(dict_in[each_col])
    for each_date in amortize_dict_in:
        if each_date not in dict_in:
            dict_in[each_date] = list()
            for i in range(len_in_dict - 1):
                dict_in[each_date].append(0.0)

        dict_in[each_date].append(amortize_dict_in[each_date])

    for each_key in dict_in:
        if each_key not in amortize_dict_in and each_key not in set_base_columns:
            dict_in[each_key].append(0.0)

    return dict_in


def change_date_col_to_datetime(df_in, set_base_col):
    col_rename_dict = dict()
    for each_col in df_in.columns:
        if each_col not in set_base_col:
            col_rename_dict[each_col] = pd.to_datetime(each_col)

    return df_in.rename(columns=col_rename_dict)


def find_earliest_and_latest_dates(df_in):
    earliest_date = None
    latest_date = None

    for each_col in df_in.columns:
        if isinstance(each_col, pd.Timestamp):
            if earliest_date is None:
                earliest_date = each_col
            if latest_date is None:
                latest_date = each_col

            if each_col > latest_date:
                latest_date = each_col
            if each_col < earliest_date:
                earliest_date = each_col

    return earliest_date, latest_date


def fill_missing_date_df(df_in, earliest_date, latest_date):
    set_date_diff = set()
    temp_date_range = pd.date_range(start=earliest_date, end=latest_date, freq="M")
    if not temp_date_range.isin(df_in.columns).all():
        array_index_diff = np.where(~temp_date_range.isin(df_in.columns))[0]
        for each_index in array_index_diff:
            if temp_date_range[each_index] not in set_date_diff:
                set_date_diff.add(temp_date_range[each_index])

    for each_date in set_date_diff:
        df_in.loc[:, each_date] = 0

    return df_in


def sort_col_by_date(df_in):
    temp_other_list = list()
    temp_date_list = list()
    num_cols = df_in.shape[1]

    for i in range(num_cols):
        if isinstance(df_in.columns[i], pd.Timestamp):
            temp_date_list.append(df_in.columns[i])
        else:
            temp_other_list.append(df_in.columns[i])

    temp_date_sorted = np.sort(temp_date_list)
    df_output = pd.concat(
        [df_in.loc[:, temp_other_list], df_in.loc[:, temp_date_sorted]], axis=1
    )

    return df_output, temp_date_sorted


def finalize_amortize_df(
    df_in,
    date_array_in,
    filter_by_col_list,
    total_paid_amount_colname,
    receipt_colname,
    vat_receipt_colname,
):
    list_output = list()
    for each_group, each_temp_df in df_in.groupby(by=filter_by_col_list):
        if len(each_temp_df) > 1:
            list_receipt = pd.unique(each_temp_df[receipt_colname])
            list_receipt_str = str(list_receipt).replace(" ", ", ")
            each_temp_df["all_related_receipt"] = list_receipt_str

            list_vat_receipt = pd.unique(each_temp_df[vat_receipt_colname])
            list_vat_receipt_str = str(list_vat_receipt).replace(" ", ", ")
            each_temp_df["all_related_vat_receipt"] = list_vat_receipt_str
        else:
            each_temp_df["all_related_receipt"] = each_temp_df[receipt_colname]
            each_temp_df["all_related_vat_receipt"] = each_temp_df[vat_receipt_colname]

        each_temp_df["Cash Received"] = each_temp_df[total_paid_amount_colname].sum()
        list_output.append(each_temp_df.iloc[[0]])

    output_df = pd.concat(list_output, axis=0)
    current_day = datetime.datetime.now()
    current_month_end_day = number_of_days(current_day.year, current_day.month)
    current_month_end = pd.Timestamp(
        day=current_month_end_day, month=current_day.month, year=current_day.year
    )
    output_df["Accumulated Amortized Value"] = 0
    output_df["Unamortized Value"] = 0

    for each_date in date_array_in:
        if current_month_end >= each_date:
            output_df.loc[:, "Accumulated Amortized Value"] += output_df.loc[
                :, each_date
            ]
        else:
            output_df.loc[:, "Unamortized Value"] += output_df.loc[:, each_date]

    return output_df


def calculate_vat_rate(
    df_in,
    total_vat_amount_colname,
    total_amount_colname,
    service_name_colname,
    vat_invoice_code_number_colname,
):
    original_vat_rate = df_in[total_vat_amount_colname] / df_in[total_amount_colname]
    na_vat_rate_boolean = original_vat_rate.isna()
    for index, each_service in df_in[service_name_colname][
        na_vat_rate_boolean
    ].iteritems():
        service_query_obj = Service.query.filter_by(name=each_service).first()
        if service_query_obj is not None:
            original_vat_rate.loc[index] = service_query_obj.vat_proportion
        else:
            if (
                df_in.loc[index, vat_invoice_code_number_colname] != ""
                and ~df_in[vat_invoice_code_number_colname].isna()[index]
            ):
                original_vat_rate.loc[index] = 1
            else:
                original_vat_rate.loc[index] = 0

    return original_vat_rate


def filter_amortize_df(df_in, start_date, end_date):
    new_start_date = datetime.datetime(
        day=1, month=start_date.month, year=start_date.year
    )
    new_end_day = number_of_days(end_date.year, end_date.month)
    new_end_date = datetime.datetime(
        day=new_end_day, month=end_date.month, year=end_date.year
    )
    target_dates = pd.date_range(new_start_date, new_end_date)

    count_found = 0
    for each_date in target_dates:
        if each_date in df_in.columns:
            if count_found == 0:
                boo_series = df_in.loc[:, each_date].abs() > 0
            else:
                boo_series = np.logical_or(
                    boo_series, df_in.loc[:, each_date].abs() > 0
                )
            count_found += 1

    return df_in[boo_series], boo_series


def filter_date(df_in, colname, start_date, end_date):
    return df_in[
        np.logical_and(
            pd.to_datetime(df_in[colname]) >= pd.to_datetime(start_date),
            pd.to_datetime(df_in[colname]) <= pd.to_datetime(end_date),
        )
    ]


def process_all_amortize_records(
    start_date_filter=None,
    end_date_filter=None,
    sales_case=None,
    amortize_date_case=None,
):
    if sales_case:
        accounting_query = Accounting_record.query.filter(
            Accounting_record.country == current_user.user_country,
            Accounting_record.date_created >= start_date_filter,
            Accounting_record.date_created <= end_date_filter,
        ).order_by(Accounting_record.id)
    else:
        accounting_query = Accounting_record.query.filter(
            Accounting_record.country == current_user.user_country
        ).order_by(Accounting_record.id)

    all_accounting_records = accounting_query.all()

    output_dict = dict()
    pre_non_vat_list_columns = [
        "code_number",
        "vat_invoice_code_number",
        "receipt_pm_code",
        "note",
        "transaction_id",
        "name",
        "name_th",
        "address",
        "date_created",
        "service",
        "service_category",
        "service_subcategory",
        "payment_method",
        "payment_date",
        "payment_time",
        "card_machine",
        "card_issuer",
        "amortization_start_date",
        "total_service_count",
        "original_price_per_unit",
        "service_count",
        "price_per_unit",
    ]
    refund_list_columns = ["refund_status", "refund_amount", "refund_date"]
    non_vat_list_columns = [
        "total_non_vat_amount",
        "tax_invoice_amount",
        "vat_amount",
        "total_vat_amount",
        "total_amount",
    ]

    list_columns = pre_non_vat_list_columns + non_vat_list_columns + refund_list_columns
    list_amortize_columns = [
        "all_related_receipt",
        "all_related_vat_receipt",
        "receipt_pm_code",
        "transaction_id",
        "name",
        "address",
        "service",
        "service_category",
        "service_subcategory",
        "payment_method",
        "payment_date",
        "payment_time",
        "card_machine",
        "card_issuer",
        "amortization_start_date",
        "total_service_count",
        "original_price_per_unit",
    ]
    set_columns = set(list_columns)

    for each_amortize_record in all_accounting_records:
        each_amortize_dict = process_each_amortize_record(each_amortize_record)
        output_dict = populate_amortize_output_dict(
            output_dict,
            each_amortize_record,
            each_amortize_dict,
            list_columns,
            set_columns,
        )

    overall_df = pd.DataFrame(output_dict)
    overall_df = change_date_col_to_datetime(overall_df, set_columns)
    overall_df_earliest_date, overall_df_latest_date = find_earliest_and_latest_dates(
        overall_df
    )
    overall_df = fill_missing_date_df(
        overall_df, overall_df_earliest_date, overall_df_latest_date
    )
    overall_df, sorted_dates = sort_col_by_date(overall_df)
    overall_df = finalize_amortize_df(
        overall_df,
        sorted_dates,
        ["transaction_id", "service"],
        "total_amount",
        "code_number",
        "vat_invoice_code_number",
    )

    accounting_df = pd.read_sql(
        accounting_query.statement, accounting_query.session.bind
    )
    accounting_df = accounting_df.replace([np.nan, "null"], ["", ""])

    if start_date_filter is not None and end_date_filter is not None and not sales_case:
        if amortize_date_case:
            overall_df, filter_boo = filter_amortize_df(
                overall_df, start_date_filter, end_date_filter
            )
            accounting_df = accounting_df.loc[filter_boo[filter_boo].index, :]

    list_amortize_val_col = list()
    vat_calculate_col = list()
    for each_col in overall_df.columns:
        if each_col in sorted_dates:
            list_amortize_val_col.append(each_col)
            vat_calculate_col.append(each_col)

    list_amortize_val_col.extend(
        ["Cash Received", "Accumulated Amortized Value", "Unamortized Value"]
    )
    vat_calculate_col.extend(["Accumulated Amortized Value", "Unamortized Value"])

    base_df = overall_df.loc[:, list_amortize_columns]
    refund_df = overall_df.loc[:, refund_list_columns]
    vat_rate = calculate_vat_rate(
        overall_df,
        "total_vat_amount",
        "total_amount",
        "service",
        "vat_invoice_code_number",
    )

    vat_df_amortize = overall_df.loc[:, list_amortize_val_col].multiply(
        vat_rate, axis="index"
    )
    vat_df_amortize.loc[:, vat_calculate_col] = (
        vat_df_amortize.loc[:, vat_calculate_col] / 1.07
    )
    non_vat_df_amortize = overall_df.loc[:, list_amortize_val_col].multiply(
        (1 - vat_rate), axis="index"
    )
    sum_vat_non_vat_df = vat_df_amortize + non_vat_df_amortize

    overall_df = pd.concat(
        [overall_df.loc[:, list_amortize_columns], sum_vat_non_vat_df, refund_df],
        axis=1,
    )
    vat_df = pd.concat([base_df, vat_df_amortize, refund_df], axis=1)
    non_vat_df = pd.concat([base_df, non_vat_df_amortize, refund_df], axis=1)

    output_dict = dict()
    if sales_case:
        accounting_df["non_vat_price_per_unit"] = (
            accounting_df["total_non_vat_amount"] / accounting_df["service_count"]
        )
        list_columns = (
            pre_non_vat_list_columns
            + ["non_vat_price_per_unit"]
            + non_vat_list_columns
            + refund_list_columns
        )
        overall_df = accounting_df.loc[:, list_columns]
        output_dict["Overall Sales Data"] = overall_df
        output_dict["VAT"] = overall_df[overall_df["total_vat_amount"].abs() > 0]
        output_dict["Non-VAT"] = overall_df[
            overall_df["total_non_vat_amount"].abs() > 0
        ]
    else:
        if not amortize_date_case:
            accounting_df = filter_date(
                accounting_df, "payment_date", start_date_filter, end_date_filter
            )
            overall_df = filter_date(
                overall_df, "payment_date", start_date_filter, end_date_filter
            )
            vat_df = filter_date(
                vat_df, "payment_date", start_date_filter, end_date_filter
            )
            non_vat_df = filter_date(
                non_vat_df, "payment_date", start_date_filter, end_date_filter
            )

        output_dict["Accounting Data"] = accounting_df
        output_dict["Overall Amortization"] = overall_df
        output_dict["VAT Amortization"] = vat_df
        output_dict["Non-VAT Amortization"] = non_vat_df

    return output_dict


def process_and_download_accounting_query(
    output_filename,
    start_date=None,
    end_date=None,
    sales_case=False,
    amortize_date_case=True,
):
    """Process the given non-VAT query and download the files given matching the descriptions in the query

    Args:
        query_obj (SQLAlchemy query object): A query object for accounting documents
        output_filename (str): string of the output filename

    Returns:
        Flask response: Response object for the Excel file
    """
    # Create a writer to write a PDF file in a form of binaries
    out = io.BytesIO()
    writer = ExcelWriter(out, engine="openpyxl")

    amortize_dict = process_all_amortize_records(
        start_date, end_date, sales_case, amortize_date_case
    )
    # Save the data frame in a form of an excel file
    for each_sheet_name in amortize_dict:
        amortize_dict[each_sheet_name].to_excel(
            writer, sheet_name=each_sheet_name, index=False
        )
    writer.save()
    out.seek(0)
    resp = make_response(out.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename={}".format(
        output_filename
    )
    resp.headers["Content-Type"] = "application/vnd.ms-excel; charset=utf-8"

    return resp


def fill_amortization_form(accounting_record_in):
    form = AmortizeEditForm()

    default_amortization_choices = ["Constant", "Fixed Hrs/Week", "Custom"]
    amortization_set = {"Constant", "Fixed Hrs/Week", "Custom"}

    if accounting_record_in.amortization_type is not None:
        amortization_choices = [accounting_record_in.amortization_type]
        amortization_choices = fill_amortization_slots(
            amortization_choices, amortization_set
        )
    else:
        amortization_choices = default_amortization_choices

    form.amortization_type.choices = amortization_choices
    form.start_date.data = accounting_record_in.start_date
    form.end_date.data = accounting_record_in.end_date

    form.total_hours.data = accounting_record_in.total_hours

    form.monday_hrs.data = accounting_record_in.monday_hrs
    form.tuesday_hrs.data = accounting_record_in.tuesday_hrs
    form.wednesday_hrs.data = accounting_record_in.wednesday_hrs
    form.thursday_hrs.data = accounting_record_in.thursday_hrs
    form.friday_hrs.data = accounting_record_in.friday_hrs
    form.saturday_hrs.data = accounting_record_in.saturday_hrs
    form.sunday_hrs.data = accounting_record_in.sunday_hrs

    form.month_1_hrs.data = accounting_record_in.month_1_hrs
    form.month_2_hrs.data = accounting_record_in.month_2_hrs
    form.month_3_hrs.data = accounting_record_in.month_3_hrs
    form.month_4_hrs.data = accounting_record_in.month_4_hrs
    form.month_5_hrs.data = accounting_record_in.month_5_hrs
    form.month_6_hrs.data = accounting_record_in.month_6_hrs

    return form


def save_amortization_record(accounting_record, form_in):
    if form_in.apply_to_related_records.data:
        this_service_records = Accounting_record.query.filter_by(
            transaction_id=accounting_record.transaction_id,
            service=accounting_record.service,
        ).all()
        if re.match(r"^Discount: ", accounting_record.service):
            related_service_name = accounting_record.service[10:]
        else:
            related_service_name = "Discount: " + accounting_record.service

        related_records = Accounting_record.query.filter_by(
            transaction_id=accounting_record.transaction_id,
            service=related_service_name,
        ).all()
        if len(related_records) == 0:
            if re.match(r"^Discount: ", accounting_record.service):
                related_service_obj = Service.query.filter_by(
                    name=related_service_name
                ).first()
                related_service_name = related_service_obj.non_vat_name
            else:
                related_service_obj = Service.query.filter_by(
                    name=accounting_record.service
                ).first()
                related_service_name = "Discount: " + related_service_obj.non_vat_name
            related_records = Accounting_record.query.filter_by(
                transaction_id=accounting_record.transaction_id,
                service=related_service_name,
            ).all()

        this_service_records.extend(related_records)

    list_output = list()
    list_output.append(datetime.datetime.utcnow())
    list_output.append(accounting_record.amortization_type)

    assert accounting_record.amortization_type in {
        "Constant",
        "Fixed Hrs/Week",
        "Custom",
    }

    if accounting_record.amortization_type == "Constant":
        list_output.append(accounting_record.start_date)
        list_output.append(accounting_record.end_date)
    elif accounting_record.amortization_type == "Fixed Hrs/Week":
        list_append = [
            accounting_record.start_date,
            accounting_record.total_hours,
            accounting_record.monday_hrs,
            accounting_record.tuesday_hrs,
            accounting_record.wednesday_hrs,
            accounting_record.thursday_hrs,
            accounting_record.friday_hrs,
            accounting_record.saturday_hrs,
            accounting_record.sunday_hrs,
        ]
        for each in list_append:
            list_output.append(each)
    else:
        list_append = [
            accounting_record.start_date,
            accounting_record.month_1_hrs,
            accounting_record.month_2_hrs,
            accounting_record.month_3_hrs,
            accounting_record.month_4_hrs,
            accounting_record.month_5_hrs,
            accounting_record.month_6_hrs,
        ]
        for each in list_append:
            list_output.append(each)

    if (
        accounting_record.former_amortization_info is None
        or accounting_record.former_amortization_info == ""
    ):
        greater_list_output = list()
        greater_list_output.append(list_output)
        accounting_record.former_amortization_info = str(greater_list_output)
    else:
        greater_list_output = eval(accounting_record.former_amortization_info)
        greater_list_output.append(list_output)
        accounting_record.former_amortization_info = str(greater_list_output)

    accounting_record.amortization_type = form_in.amortization_type.data
    accounting_record.start_date = form_in.start_date.data
    accounting_record.end_date = form_in.end_date.data

    accounting_record.total_hours = form_in.total_hours.data
    accounting_record.monday_hrs = form_in.monday_hrs.data
    accounting_record.tuesday_hrs = form_in.tuesday_hrs.data
    accounting_record.wednesday_hrs = form_in.wednesday_hrs.data
    accounting_record.thursday_hrs = form_in.thursday_hrs.data
    accounting_record.friday_hrs = form_in.friday_hrs.data
    accounting_record.saturday_hrs = form_in.saturday_hrs.data
    accounting_record.sunday_hrs = form_in.sunday_hrs.data

    accounting_record.month_1_hrs = form_in.month_1_hrs.data
    accounting_record.month_2_hrs = form_in.month_2_hrs.data
    accounting_record.month_3_hrs = form_in.month_3_hrs.data
    accounting_record.month_4_hrs = form_in.month_4_hrs.data
    accounting_record.month_5_hrs = form_in.month_5_hrs.data
    accounting_record.month_6_hrs = form_in.month_6_hrs.data

    if form_in.apply_to_related_records:
        for each_record in this_service_records:
            each_record.former_amortization_info = str(greater_list_output)

            each_record.amortization_type = form_in.amortization_type.data
            each_record.start_date = form_in.start_date.data
            each_record.end_date = form_in.end_date.data

            each_record.monday_hrs = form_in.monday_hrs.data
            each_record.tuesday_hrs = form_in.tuesday_hrs.data
            each_record.wednesday_hrs = form_in.wednesday_hrs.data
            each_record.thursday_hrs = form_in.thursday_hrs.data
            each_record.friday_hrs = form_in.friday_hrs.data
            each_record.saturday_hrs = form_in.saturday_hrs.data
            each_record.sunday_hrs = form_in.sunday_hrs.data

            each_record.month_1_hrs = form_in.month_1_hrs.data
            each_record.month_2_hrs = form_in.month_2_hrs.data
            each_record.month_3_hrs = form_in.month_3_hrs.data
            each_record.month_4_hrs = form_in.month_4_hrs.data
            each_record.month_5_hrs = form_in.month_5_hrs.data
            each_record.month_6_hrs = form_in.month_6_hrs.data

    db.session.commit()

    return accounting_record.id
