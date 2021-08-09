from datetime import date, timedelta
from gcsa.google_calendar import GoogleCalendar
from google.oauth2.credentials import Credentials
from matplotlib.ticker import MaxNLocator
import numpy as np
import os
import pandas as pd


class Timesheet():

    def __init__(self, days=90):
        self.__gcal_credentials__ = self.__get_gcal_credentials__()
        self.end = date.today()
        self.start = self.end - timedelta(days=days)
        self.data = self.__get_timesheet__()
        self.status = f"Clocked {'On' if self.data.iloc[-1]['clocked_off'] is None else 'Off'}"

    def __get_gcal_credentials__(self):
        """Fetch credentials from env to authenticate against calendar."""
        return Credentials(token=os.environ["TOKEN"],
                           refresh_token=os.environ["REFRESH_TOKEN"],
                           client_id=os.environ["CLIENT_ID"],
                           client_secret=os.environ["CLIENT_SECRET"],
                           token_uri="https://oauth2.googleapis.com/token")

    def __get_timecards__(self):
        """Fetch calendar events with 'clocked' in title."""
        calendar = GoogleCalendar(credentials=self.__gcal_credentials__)
        return calendar.get_events(time_min=self.start,
                                   time_max=self.end,
                                   query="clocked")

    def __get_timesheet__(self):
        """Construct pandas DataFrame of clock on / clock off events."""
        # Create DataFrame from gcsa events
        cards = pd.DataFrame([{"time": timecard.start,
                               "event": timecard.summary}
                              for timecard in self.__get_timecards__()])

        # Preallocate dataframe for transformed data
        sheet = pd.DataFrame({"clocked_on": None,
                              "clocked_off": None},
                              index=cards["time"].dt.date.unique())

        # Loop over cards and add to correct position in timesheet
        for i, row in cards.iterrows():
            event_type = "clocked_on" if "on" in row["event"].lower() else "clocked_off"
            sheet.loc[row["time"].date(), event_type] = row["time"].time()

        # Compute hours worked from clocked on and clocked off data
        sheet["shift_length"] = (
            pd.to_datetime(sheet["clocked_off"].dropna().astype(str), format='%H:%M:%S')
            - pd.to_datetime(sheet["clocked_on"].dropna().astype(str), format='%H:%M:%S')
        ).dt.seconds / (60 ** 2)

        return sheet

    def get_last_n_shifts(self, n=90):
        return self.data.dropna().iloc[-n:]

    def summarise(self, n=90, dp=2, agg=None):
        if agg is None:
            agg = {"Total Hours Worked": np.sum,
                   "Average Working Day": np.median,
                   "Shortest Working Day": np.min,
                   "Longest Working Day": np.max}
        return self.get_last_n_shifts(n)["shift_length"].agg(agg).round(dp)

    def hist(self, n=90):
        ax = self.get_last_n_shifts(n)["shift_length"].plot(kind="hist")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_xlabel("Length of working day (Hours)")
        ax.set_ylabel("Frequency")
        return ax.get_figure(), ax

    def time_series(self, n=90):
        ax = self.get_last_n_shifts(n)["shift_length"].plot(legend=False, rot=45)
        ax.set_ylabel("Length of working day (Hours)")
        ax.set_xlabel("Date")
        return ax.get_figure(), ax

    def boxplot(self, n=90):
        c = "C0"
        ax = self.get_last_n_shifts(n)["shift_length"].plot(
            kind="box",
            vert=False,
            boxprops=dict(color=c),
            capprops=dict(color=c),
            whiskerprops=dict(color=c),
            flierprops=dict(color=c, markeredgecolor=c),
            medianprops=dict(color=c))
        ax.set_yticks([])
        ax.set_xlabel("Length of working day (Hours)")
        return ax.get_figure(), ax
