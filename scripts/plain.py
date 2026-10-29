AGE="Adjusted for age."
PL="CDC PLACES estimate for 2023, modeled from a national health survey and adjusted for age. PLACES publishes county estimates only, so the chart shows how the county ranks among California's 58 counties."
PQI="HCAI rate for 2024, adjusted for age, sex, and poverty. These hospital stays can often be prevented with good outpatient care. HCAI changed its method in 2023 and 2024, so earlier years are not shown."
ACS="U.S. Census Bureau American Community Survey estimate for 2020 to 2024. Estimates for small counties have wider margins of error."
SM="DHCS count for fiscal year 2022-23. DHCS publishes counts for this measure and does not publish rates. DHCS withholds small counts to protect privacy."
HP="The Health Resources and Services Administration (HRSA) designates places and populations with too few providers, and scores each designation from 0 to 25. A higher score means a greater shortage. A county can hold several designations: a geographic area, a population group such as low-income residents, or a clinic that serves underserved patients. The value shown is the score of the county's highest-scoring designation. A value of 0 means the county has no designation."
MC="U.S. Census Bureau American Community Survey estimate for 2020 to 2024. Includes Medi-Cal and other public health coverage based on income (means-tested coverage)."
P={
"hdmort":[("Heart disease deaths per 100,000 adults ages 35 and older","CDC rate for 2022 to 2024, adjusted for age. CDC smooths county rates using data from nearby counties so small-county rates are more stable.")],
"strokemort":[("Stroke deaths per 100,000 adults ages 35 and older","CDC rate for 2022 to 2024, adjusted for age. CDC smooths county rates using data from nearby counties so small-county rates are more stable.")],
"places":[("Adults with high blood pressure",PL),("Adults with coronary heart disease",PL)],
"placesRisk":[("Adults with diagnosed diabetes",PL),("Adults with obesity",PL),("Adults who smoke cigarettes",PL)],
"placesBPmed":[("Adults with high blood pressure who take medicine for it",PL),("Adults with a routine checkup in the past year",PL)],
"placesSocial":[("Adults with food insecurity in the past year",PL),("Adults without reliable transportation in the past year",PL)],
"placesMH":[("Adults with frequent mental distress",PL),("Adults with depression",PL)],
"placesAlc":[("Adults who binge drink",PL),("Adults who smoke cigarettes",PL)],
"placesSupport":[("Adults who lack social and emotional support",PL),("Adults who feel lonely",PL)],
"placesHousing":[("Adults unable to pay rent, mortgage, or utility bills in the past year",PL)],
"placesAccess":[("Adults ages 18 to 64 without health insurance",PL),("Adults with a routine checkup in the past year",PL)],
"pqiCardiac":[("Preventable hospital stays for heart failure per 100,000 adults",PQI),("Preventable hospital stays for high blood pressure per 100,000 adults",PQI)],
"pqiAll":[("Preventable hospital stays per 100,000 adults, all conditions",PQI)],
"pqiKids":[("Preventable hospital stays per 100,000 children ages 6 to 17",PQI+" HCAI withholds rates for counties with small numbers."),("Asthma hospital stays per 100,000 children ages 2 to 17",PQI+" HCAI withholds rates for counties with small numbers.")],
"hpsaPC":[("Federal primary care shortage score for the county's highest-need area, population, or clinic. Higher scores mean a greater shortage.",HP)],
"hpsaMH":[("Federal mental health shortage score for the county's highest-need area, population, or clinic. Higher scores mean a greater shortage.",HP)],
"acsPov":[("People living below the federal poverty level",ACS),("People without health insurance",ACS)],
"acsChild":[("Children under 18 living below the federal poverty level",ACS)],
"acsYoung":[("Children under 5 living below the federal poverty level",ACS)],
"suicide":[("Suicide deaths per 100,000 residents","CDPH rate for 2021 to 2023, adjusted for age. CDPH flags rates based on a small number of deaths, which can change a lot from year to year. Flagged counties: Colusa, Del Norte, Glenn, and Trinity.")],
"od":[("Drug overdose deaths per 100,000 residents","CDPH rate for 2021 to 2023, adjusted for age. CDPH flags rates based on a small number of deaths, which can change a lot from year to year. Flagged counties: Colusa and Trinity.")],
"births":[("Births to mothers ages 15 to 19 per 1,000 females ages 15 to 19","CDPH rate for 2021 to 2023.")],
"smhs05":[("Number of Medi-Cal children ages 3 to 5 who received at least 1 specialty mental health service",SM),("Number of Medi-Cal children ages 3 to 5 who received at least 5 specialty mental health services",SM)],
"smhsYouth":[("Number of Medi-Cal children and youth ages 0 to 20 who received at least 1 specialty mental health service",SM),("Number of Medi-Cal children and youth ages 0 to 20 who received at least 5 specialty mental health services",SM)],
"medical":[("Residents with Medi-Cal or other income-based public coverage",MC)],
"medicalKids":[("Children and youth under 19 with Medi-Cal or other income-based public coverage",MC)],
"cdeGrad":[("Students who graduated high school in four years","CDE four-year adjusted cohort graduation rate: students who earned a regular high school diploma within four years of starting grade 9.")],
"jailRate":[("People in jail per 100,000 residents ages 15 to 64","Vera Institute of Justice rate, from Bureau of Justice Statistics and state and local jail data. Average daily jail population.")],
"chrProviders":[("Residents per mental health provider","County Health Rankings & Roadmaps ratio. Mental health providers include psychiatrists, psychologists, licensed clinical social workers, counselors, marriage and family therapists, and advanced practice nurses specializing in mental health care."),("Residents per primary care physician","County Health Rankings & Roadmaps ratio. Primary care physicians practice general practice, family medicine, internal medicine, or pediatrics.")],
"acsUnins6":[("Children under 6 without health insurance","Census ACS 5-year estimate, published with a margin of error.")],
"cdeAbs":[("Students in grades K to 12 who were chronically absent","CDE rate. A student is chronically absent after missing 10 percent or more of school days. CDE published no data for 2019-20 because of COVID-19.")],
"cdeHomeless":[("Number of students who experienced homelessness during the school year","CDE count, including students living doubled up, in shelters, in motels, or unsheltered. CDE changed how districts confirm housing status in 2025-26, so the 2025-26 count is not directly comparable with earlier years.")],
"bhHousing":[("Medi-Cal members who experienced homelessness, per 10,000 members","DHCS rate for fiscal year 2024-25. Sutter County shows the combined Sutter-Yuba value DHCS publishes."),("Medi-Cal members with significant behavioral health needs who experienced homelessness, per 10,000 of these members","DHCS rate for fiscal year 2024-25. Sutter County shows the combined Sutter-Yuba value DHCS publishes.")],
"hdis":[("People experiencing homelessness who used homeless response services","Homeless Data Integration System count for 2025. The count covers the whole Continuum of Care, so counties that share a Continuum of Care show the same number.")],
"ecm":[("Medi-Cal managed care members who received Enhanced Care Management (ECM)","DHCS county rate for 2025. DHCS publishes a statewide member count and does not publish a statewide rate."),("Number of members who received ECM","DHCS count for 2025.")],
}

BHP="DHCS Behavioral Health Transformation performance measure for fiscal year 2024-25, from the Behavioral Health Public County Profile. California is the DHCS statewide value. DHCS withholds small counts to protect privacy."
PLAN="From the county's Behavioral Health Services Act (BHSA) Integrated Plan for fiscal year 2026-27, as published by DHCS in the Behavioral Health Public County Profile. Counties submit these plans; DHCS publishes no statewide value."
CHSP="CDPH County Health Status Profiles, 2021 to 2023, adjusted for age. CDPH flags rates based on a small number of deaths, which can change a lot from year to year."
P.update({
"chdmort":[("Coronary heart disease deaths per 100,000 residents",CHSP+" CDPH flags none of the 17 counties for this measure.")],
"diabmort":[("Diabetes deaths per 100,000 residents",CHSP+" Flagged counties: Colusa and Trinity.")],
"infmort":[("Infant deaths per 1,000 live births","CDPH County Health Status Profiles, births in 2020 to 2022. CDPH withholds rates for small counties and flags rates based on a small number of infant deaths, which can change a lot from year to year. Flagged counties: Glenn, Humboldt, Mendocino, Tehama, Marin, and Napa.")],
"lbw":[("Babies born at low birthweight","CDPH County Health Status Profiles, 2021 to 2023. Low birthweight means under 2,500 grams (5.5 pounds).")],
"prenatal":[("Births with prenatal care that began in the first trimester","CDPH County Health Status Profiles, 2021 to 2023.")],
"firearm":[("Firearm deaths per 100,000 residents",CHSP+" Flagged counties: Colusa, Del Norte, Glenn, and Trinity.")],
"homicide":[("Homicide deaths per 100,000 residents",CHSP+" CDPH flags the rate in 11 of the 17 counties.")],
"mvc":[("Motor vehicle crash deaths per 100,000 residents",CHSP+" Flagged counties: Colusa, Del Norte, Glenn, and Trinity.")],
"bhPerfAccess":[("Emergency visits for mental illness followed by a mental health service within 7 days",BHP),("Emergency visits for substance use followed by a substance use service within 7 days",BHP),("Hospital stays for mental illness followed by a mental health service within 7 days",BHP),("New substance use disorder episodes with treatment started within 14 days",BHP)],
"bhPerfServices":[("Medi-Cal members with significant mental health needs who received at least 1 behavioral health service",BHP),("Medi-Cal members with significant mental health needs who received at least 3 behavioral health services",BHP),("Medi-Cal members with significant behavioral health needs experiencing or at risk of homelessness who received housing services",BHP)],
"bhPerfFoster":[("Children and youth ages 0 to 20 in foster care, per 10,000 Medi-Cal members ages 0 to 20",BHP),("Children and youth in foster care who received specialty mental health services",BHP)],
"bhPlanServed":[("People the county plans to serve in housing services",PLAN),("People the county plans to serve in mental health services",PLAN),("People the county plans to serve in substance use disorder services",PLAN)],
"bhPlanCost":[("Planned spending on housing services",PLAN),("Planned spending on mental health services",PLAN),("Planned spending on substance use disorder services",PLAN)],
"bhPlanAlloc":[("Share of planned Behavioral Health Services Act (BHSA) funds for Behavioral Health Services and Supports",PLAN+" The three shares add to 100 percent."),("Share of planned BHSA funds for Full Service Partnerships",PLAN),("Share of planned BHSA funds for Housing Interventions",PLAN)],
"bhPen":[("Medi-Cal members who received county mental health services","DHCS Behavioral Health Public County Profile, calendar year 2024. DHCS publishes no statewide value. Sutter shares a behavioral health system with Yuba County."),("Medi-Cal members who received substance use disorder treatment through the county","DHCS Behavioral Health Public County Profile, calendar year 2024. DHCS publishes no statewide value. Sutter shares a behavioral health system with Yuba County.")],
"wic":[("Number of pregnant people enrolled in WIC","CDPH count of certified WIC participants in December 2024. WIC is the Special Supplemental Nutrition Program for Women, Infants, and Children."),("Number of infants under age 1 enrolled in WIC","CDPH count of certified WIC participants in December 2024.")],
"hdis":[("Number of people who experienced homelessness and used homeless response services, Continuum of Care region","Homeless Data Integration System count for 2025. The count covers the whole Continuum of Care, so counties that share a Continuum of Care show the same number."),("Number of people who moved from homelessness into permanent housing, Continuum of Care region","Homeless Data Integration System count for 2025, for the whole Continuum of Care."),("People who returned to homelessness within 6 months of moving into permanent housing, Continuum of Care region","Homeless Data Integration System rate for 2025, for the whole Continuum of Care.")],
"asthmaED":[("Asthma emergency department visits per 10,000 residents","CDPH California Breathing rate for 2023, adjusted for age, using HCAI emergency department data."),("Asthma emergency department visits per 10,000 children ages 0 to 17","CDPH California Breathing rate for 2023 using HCAI emergency department data.")],
"acsHousing":[("Renter households paying 35 percent or more of income on rent","U.S. Census Bureau American Community Survey estimate for 2020 to 2024. The Census Bureau publishes this band directly."),("Homeowners with a mortgage paying 35 percent or more of income on housing","U.S. Census Bureau American Community Survey estimate for 2020 to 2024.")],
"acsVehicle":[("Households with no vehicle","U.S. Census Bureau American Community Survey estimate for 2020 to 2024. Trinity County's estimate has a wide margin of error.")],
"acsBroadband":[("Households with a broadband internet subscription","U.S. Census Bureau American Community Survey estimate for 2020 to 2024.")],
"acsDisability":[("People with a disability","U.S. Census Bureau American Community Survey estimate for 2020 to 2024.")],
"acsLanguage":[("People age 5 and older who speak English less than very well","U.S. Census Bureau American Community Survey estimate for 2020 to 2024. Trinity County's estimate has a wide margin of error.")],
})
