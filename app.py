import streamlit as st
import pandas as pd
import requests
import io

def check_password():
    password = st.text_input("Wprowadź hasło:", type="password")
    if password == "HNRO2025":
        return True
    elif password:
        st.error("Nieprawidłowe hasło.")
        return False
    else:
        return False

if not check_password():
    st.stop()

st.title("Slotoloty")

# 📥 Pobieranie danych z Dropbox
dropbox_excel_url = "https://www.dropbox.com/scl/fi/ztkqbib2ntb4geoi4bes4/slotyw25.xlsx?rlkey=31v8vf7n6lbai3udc16nmov3z&st=lkqayt5p&dl=1"

try:
    response = requests.get(dropbox_excel_url)
    response.raise_for_status()
    df1 = pd.read_excel(io.BytesIO(response.content), engine="openpyxl")
    df1 = df1.drop(df1.columns[3:9], axis=1)
    df1 = df1[["Numer rejsu", "Dzień Tyg", "Airport", "Dopuszczalne anulacje"]]
except Exception as e:
    st.error(f"Błąd podczas pobierania pliku sloty.xlsx z Dropbox: {e}")
    st.stop()

# 📤 Wgranie pliku testowego przez użytkownika
uploaded_file = st.file_uploader("Wgraj plik testowe.xlsx", type=["xlsx"])

if uploaded_file:
    try:
        df5 = pd.read_excel(uploaded_file, engine="openpyxl")
        df5 = df5.drop(columns=["NO", "Al", "OS", "Own", "A/C", "Cfg", "Seats", "Srv", "Class", "Blkt", "Cntxt", "Reason", "Act", "Change", "Time", "By"])
        df5['Date'] = pd.to_datetime(df5['Date']).dt.date
        
        df5.columns = ["Numer rejsu", "Date", "Dzień Tyg", "Org","STD (UTC)","STA (UTC)","+", "Dest"]
        df5 = df5[["Numer rejsu", "Date", "Dzień Tyg", "STD (UTC)", "STA (UTC)", "+", "Org", "Dest"]]
        df5['STA (UTC)'] = df5['STA (UTC)'].apply(lambda x: str(x).split()[2])
        dni_map = {'MON': 1, 'TUE': 2, 'WED': 3, 'THU': 4, 'FRI': 5, 'SAT': 6, 'SUN': 7}
        df5['Dzień Tyg'] = df5['Dzień Tyg'].str.strip().map(dni_map)
        df5 = df5.dropna()

        def przesun_dzien(dzien):
            try:
                dzien = int(dzien)
                return 1 if dzien == 7 else dzien + 1
            except:
                return dzien

        # 🔄 Rozbijanie wierszy na dwa
        nowe_wiersze = []
        for _, row in df5.iterrows():
            numer = row['Numer rejsu']
            dzien = row['Dzień Tyg']
            plus = row['+']
            org = row['Org']
            dest = row['Dest']
            date = row['Date']
            std = row['STD (UTC)']
            sta = row['STA (UTC)']

            nowe_wiersze.append({'Numer rejsu': numer, 'Dzień Tyg': dzien, 'Port': org, 'Date': date, 'STD (UTC)': std, 'STA (UTC)': sta})
            nowe_wiersze.append({'Numer rejsu': numer, 'Dzień Tyg': przesun_dzien(dzien) if plus == 1 else dzien,
                                 'Port': dest, 'Date': date, 'STD (UTC)': std, 'STA (UTC)': sta})

        df6 = pd.DataFrame(nowe_wiersze)
        df6 = df6.rename(columns={'Port': 'Airport'})

        # 🔗 Łączenie z danymi z Dropbox
        df6_uzupelniony = df6.merge(df1, on=['Airport', 'Numer rejsu', 'Dzień Tyg'], how='left')

        # 🔁 Łączenie wierszy parami
        def polacz_wiersze_parami(df):
            polaczone_wiersze = []
            for i in range(0, len(df) - 1, 2):
                w1 = df.iloc[i]
                w2 = df.iloc[i + 1]
                nowy_wiersz = {
                    'Numer rejsu': w1['Numer rejsu'],
                    'Dzień Tyg': w1['Dzień Tyg'],
                    'Date': w1['Date'],
                    'STD (UTC)': w1['STD (UTC)'],
                    'STA (UTC)': w1['STA (UTC)'],
                    'Airport': w1['Airport'],
                    'Dopuszczalne anulacje': w1['Dopuszczalne anulacje'],
                    'Airport2': w2['Airport'],
                    'Dopuszczalne anulacje2': w2['Dopuszczalne anulacje']
                }
                polaczone_wiersze.append(nowy_wiersz)
            return pd.DataFrame(polaczone_wiersze)

        df_final = polacz_wiersze_parami(df6_uzupelniony)

        # 📁 Eksport do Excela
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False)
        output.seek(0)

        st.success("Dane zostały przetworzone pomyślnie.")
        st.download_button(label="Pobierz wynikowy plik Excel",
                           data=output,
                           file_name="propozycje_anulacji.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"Wystąpił błąd podczas przetwarzania pliku: {e}")
