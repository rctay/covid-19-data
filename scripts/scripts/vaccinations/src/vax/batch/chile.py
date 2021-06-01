import pandas as pd


class Chile:
    def __init__(self, source_url: str, source_url_ref: str, source_url_age: str, location: str):
        """Constructor.

        Args:
            source_url (str): Source data url
            location (str): Location name
        """
        self.source_url = source_url
        self.source_url_ref = source_url_ref
        self.source_url_age = source_url_age
        self.location = location

    def read(self) -> pd.DataFrame:
        return pd.read_csv(self.source_url)

    def read_age(self) -> pd.DataFrame:
        return pd.read_csv(self.source_url_age)

    def pipe_melt(self, df: pd.DataFrame, id_vars: list) -> pd.DataFrame:
        return df.melt(id_vars, var_name="date", value_name="value")

    def pipe_filter_rows(self, df: pd.DataFrame, colname: str) -> pd.DataFrame:
        return df[(df[colname] != "Total") & (df.value > 0)]

    def pipe_pivot(self, df: pd.DataFrame, index: list) -> pd.DataFrame:
        return df.pivot(index=index, columns="Dose", values="value").reset_index()

    def pipe_vaccinations(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df
            .assign(total_vaccinations=df.First.fillna(0) + df.Second.fillna(0))
            .rename(columns={"First": "people_vaccinated", "Second": "people_fully_vaccinated"})
        )

    def pipe_rename_vaccines(self, df: pd.DataFrame) -> pd.DataFrame:
        vaccine_mapping = {
            "Pfizer": "Pfizer/BioNTech",
            "Sinovac": "Sinovac",
            "Astra-Zeneca": "Oxford/AstraZeneca"
        }
        assert set(df["Type"].unique()) == set(vaccine_mapping.keys())
        return df.replace(vaccine_mapping)

    def pipe_aggregate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df
            .sort_values("Type")
            .groupby("date", as_index=False)
            .agg(
                people_vaccinated=("people_vaccinated", "sum"),
                people_fully_vaccinated=("people_fully_vaccinated", "sum"),
                total_vaccinations=("total_vaccinations", "sum"),
                vaccine=("Type", ", ".join),
            )
        )

    def pipe_location(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generalized."""
        return df.assign(location=self.location)

    def pipe_source(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generalized."""
        return df.assign(source_url=self.source_url_ref)

    def pipeline_base(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df
            .pipe(self.pipe_melt, ["Type", "Dose"])
            .pipe(self.pipe_filter_rows, "Type")
            .pipe(self.pipe_pivot, ["Type", "date"])
            .pipe(self.pipe_vaccinations)
            .pipe(self.pipe_rename_vaccines)
        )

    def pipeline_vaccinations(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df
            .pipe(self.pipe_aggregate_metrics)
            .pipe(self.pipe_source)
            .pipe(self.pipe_location)
        )

    def pipeline_manufacturer(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df[["Type", "date", "total_vaccinations"]]
            .rename(columns={"Type": "vaccine"})
            .assign(location="Chile")
            .sort_values("date")
        )

    def pipe_postprocess_age(self, df: pd.DataFrame) -> pd.DataFrame:
        regex = r"(\d{1,2})(?:[ a-zA-Z]+|-(\d{1,2})[ a-zA-Z]*)"
        df[["age_group_min", "age_group_max"]] = df.Age.str.extract(regex)
        df = df[["date", "age_group_min", "age_group_max", "total_vaccinations", "location"]]
        return df

    def pipeline_age(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df
            .pipe(self.pipe_melt, ["Age", "Dose"])
            .pipe(self.pipe_filter_rows, "Age")
            .pipe(self.pipe_pivot, ["Age", "date"])
            .pipe(self.pipe_vaccinations)
            .pipe(self.pipe_location)
            .pipe(self.pipe_postprocess_age)
            .sort_values(by="date")
        )

    def to_csv(self, paths):
        df = self.read().pipe(self.pipeline_base)
        df_age = self.read_age().pipe(self.pipeline_age)
        # Main data
        df.pipe(self.pipeline_vaccinations).to_csv(
            paths.tmp_vax_out(self.location),
            index=False
        )
        # Manufacturer
        df.pipe(self.pipeline_manufacturer).to_csv(
            paths.tmp_vax_out_man(self.location),
            index=False
        )
        # Age
        df_age.to_csv(
            paths.tmp_vax_out_by_age_group(self.location),
            index=False
        )


def main(paths):
    Chile(
        location="Chile",
        source_url="https://github.com/juancri/covid19-vaccination/raw/master/output/chile-vaccination-type.csv",
        source_url_ref="https://www.gob.cl/yomevacuno/",
        source_url_age=(
            "https://raw.githubusercontent.com/juancri/covid19-vaccination/master/output/chile-vaccination-ages.csv"
        )
    ).to_csv(paths)


if __name__ == "__main__":
    main()
