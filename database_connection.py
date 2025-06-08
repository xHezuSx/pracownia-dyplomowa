import pymysql
from datetime import datetime

host = "localhost"
user = "root"
password = ""
database = "gpw data"


try:
    connection = pymysql.connect(
        host=host, user=user, password=password, database=database
    )

    kursor = connection.cursor()

    def wstaw_firme(firma):
        sql = "INSERT INTO firma(nazwa)VALUES(%s)"
        kursor.execute(sql, firma)
        connection.commit()

    def wstaw_dane(
        data,
        tytul_raportu,
        typ_raportu,
        kategoria_raportu,
        zmiana,
        kurs,
        link,
        Id_firmy,
    ):
        sql = "INSERT INTO dane(data,tytul_raportu,typ_raportu,kategoria_raportu,zmiana,kurs,link,Id_firmy) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)"
        val = (
            data,
            tytul_raportu,
            typ_raportu,
            kategoria_raportu,
            zmiana,
            kurs,
            link,
            Id_firmy,
        )
        kursor.execute(sql, val)
        connection.commit()

    def pobierz_klucz_firmy(firma):
        mysql = "SELECT id_firmy FROM firma WHERE nazwa LIKE %s "
        kursor.execute(mysql, firma)
        return kursor.fetchone()[0]

    def wstaw_historie(
        company_name,
        report_amount,
        download_type,
        report_date,
        report_type,
        report_category,
    ):
        if report_date == "":
            sql = "INSERT INTO historia(company_name, report_amount, download_type, report_type, report_category) VALUES(%s,%s,%s,%s,%s)"
            val = (
                company_name,
                report_amount,
                download_type,
                report_type,
                report_category,
            )
            kursor.execute(sql, val)
            connection.commit()
        else:
            report_date = datetime.strptime(report_date, "%d-%m-%Y")
            datetime.strftime(report_date, "%Y-%m-%d")
            sql = "INSERT INTO historia(company_name, report_amount, download_type, report_date, report_type, report_category) VALUES(%s,%s,%s,%s,%s,%s)"
            val = (
                company_name,
                report_amount,
                download_type,
                report_date,
                report_type,
                report_category,
            )
            kursor.execute(sql, val)
            connection.commit()

    def pokaz_historie():
        sql = "SELECT company_name, report_amount, download_type, report_date, report_type, report_category FROM historia order by id desc LIMIT 2"
        kursor.execute(sql)
        return kursor.fetchall()

except pymysql.Error as e:
    print("Błąd połączenia", e)
