# PHIL Community Health Data Dashboard

Public data on health needs and services in the 17 California counties where the Population Health
Innovation Lab (PHIL) works, alongside PHIL's work with community partners.

Live site: https://dashboard.pophealthinnovationlab.org (once DNS is set up; see docs/SETUP.md)

## How it works

```
scripts/        one Python script per data source; each writes data/out/<indicator>.json
data/out/       the pulled data, saved in the repository after every refresh
data/manual/    resources.json: the links on the Resources page (edit this file to add a resource)
                actions.json: the How Partners Can Act section on each topic page
site/           the dashboard page template, its runtime, images, and the CNAME for the subdomain
build/          build_site.py assembles public/index.html; check_data.py validates the pulls
.github/        workflows: quarterly data refresh, and a rebuild when the page or resources change
```

Every value on the dashboard is published by its source. The scripts do not calculate rates or
statewide figures. A county is compared with California only when one dataset publishes both.

## Refresh schedule

* **Quarterly data refresh** (`refresh.yml`): the 15th of February, May, August, and November.
  Pulls every source, checks the data, saves it to the repository, rebuilds, and publishes the page.
  Can also be started by hand from the Actions tab ("Run workflow"); name one or more scripts to
  refresh only those, for example `ecm places`.
* **Rebuild only** (`publish.yml`): every Monday, and whenever `site/`, `data/manual/`, or `build/`
  changes on the main branch. Uses the data already in the repository. This is how an edit to
  `resources.json` reaches the live page within minutes.

If a pull fails, the workflow fails and GitHub emails the repository owner. The previous data stays
live until the problem is fixed, because `check_data.py` stops the build before anything is published.

## Updating things

| Task | What to do |
|---|---|
| Add or change a resource link | Edit `data/manual/resources.json` on GitHub and commit. The page rebuilds automatically. |
| Update a How Partners Can Act item | Edit `data/manual/actions.json` on GitHub and commit. Review these links each quarter. The page rebuilds automatically. |
| Change text on the page | Edit `site/template.html`. Keep the `__INDD__`, `__ECMD__`, `__ECMD_PUB__`, `__ECM_USE__`, and `__RES__` placeholders. |
| Change which measures a topic shows | In `site/template.html`, edit the `indicators:` lists in `TOPICS` and the `IND` entries. |
| Change measure wording | Edit `scripts/plain.py` (labels and "About this data" notes). |
| New school year of CDE data | Add the new file names to `ABS_FILES` and `HSE_FILES` in `scripts/cde.py`. |
| New CDC PLACES or mortality release | Update the dataset ids at the top of `scripts/places.py` and `scripts/cvd_mortality.py`. |
| Remove the "Prototype for Team Review" label | Delete that `<span>` in `site/template.html`. |
| Refresh the Claude prototype copy | `python3 build/fill_prototype.py <Main.dc.html>` then republish it; `build/make_template.py` goes the other way. |

## Running locally

```
pip install -r requirements.txt
export CENSUS_API_KEY=...        # free key from https://api.census.gov/data/key_signup.html
python3 scripts/run_all.py       # pull everything (about 10 minutes)
python3 build/check_data.py
python3 build/build_site.py      # writes public/index.html
cd public && python3 -m http.server 8000   # then open http://localhost:8000
```

## Data sources

| Source | Script | Used for |
|---|---|---|
| CDC PLACES, 2025 release | places.py | Chronic conditions, mental health, social needs (county only) |
| CDC heart disease and stroke mortality | cvd_mortality.py | Cardiovascular deaths |
| CDPH County Health Status Profiles | suicide.py, births.py, od.py, chsp_more.py | Suicide, adolescent births, drug overdose, coronary heart disease, diabetes, firearm, homicide and motor vehicle deaths; infant mortality, low birthweight, prenatal care |
| HCAI preventable hospitalizations | hcai.py | Adult and child preventable hospital stays |
| HRSA shortage areas | hpsa.py | Primary care and mental health shortage scores |
| U.S. Census Bureau ACS 5-year | acs.py, acs_medicaid.py, acs_more.py | Poverty, uninsured, Medi-Cal coverage, housing cost burden, vehicles, broadband, disability, language |
| DHCS behavioral health performance data | dhcs_smhs.py | Children's specialty mental health services |
| DHCS Behavioral Health Public County Profile | dhcs_bh_housing.py, dhcs_bh_profile.py | Homelessness rates, Behavioral Health Transformation performance measures, BHSA Integrated Plan projections, county penetration rates |
| DHCS Medi-Cal managed care enrollment | dhcs_mcp_enrollment.py | Plan enrollment on the ECM page |
| CDPH asthma ED visit rates and WIC participants | hcai_asthma.py, cdph_wic.py | Asthma emergency visits, WIC enrollment |
| HDIS system performance measures | hdis.py | People using homeless response services |
| CDE absenteeism and homeless enrollment | cde.py | Chronic absenteeism, students experiencing homelessness |
| DHCS ECM and Community Supports tables | ecm.py | ECM and Community Supports page |
