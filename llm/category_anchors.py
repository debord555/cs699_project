"""Example headlines for each category.

categorize.py averages each category's examples into one vector and gives an
article the category whose vector is closest to it. To make a category catch
more articles, add headlines that look like the ones it is missing.

Keys must match `categories.name` in the database. 'Other' has no examples:
an article gets it when no category is close enough.
"""

ANCHORS = {
    "Politics": [
        "BJP and Congress trade barbs ahead of assembly elections",
        "Chief Minister announces cabinet reshuffle after meeting party leaders",
        "Election Commission announces dates for bypolls in three constituencies",
        "Opposition MLAs walk out of the assembly over the new bill",
        "Party workers hold rally as leader files nomination for Lok Sabha seat",
    ],
    "Crime": [
        "Police arrest two men for murder after body found near railway track",
        "Woman raped and assaulted, accused absconding, FIR registered",
        "Drugs worth Rs 2 crore seized, three held by police",
        "Cyber fraud: man loses Rs 10 lakh to fake investment scheme, case registered",
        "Court denies bail to accused in corruption case, ED raids premises",
    ],
    "Business & Finance": [
        "Company posts 20% rise in quarterly net profit, shares jump",
        "Sensex and Nifty close higher as markets rally",
        "RBI keeps repo rate unchanged, inflation forecast revised",
        "Startup raises $50 million in funding round led by investors",
        "Petrol and gold prices rise again this week",
    ],
    "Education": [
        "Board exam results declared, students score high pass percentage",
        "University announces admission schedule for undergraduate courses",
        "Teachers protest over pending salaries at government schools",
        "IIT students and faculty raise concerns over campus policy",
        "NEET and JEE exam dates announced by testing agency",
    ],
    "Health": [
        "Dengue cases rise in the city as hospitals see more patients",
        "Doctors at government hospital perform rare surgery",
        "Health department launches vaccination drive in rural areas",
        "New study links diet to higher risk of heart disease",
        "Shortage of medicines and staff at district hospital",
    ],
    "Sports": [
        "India beat Australia by six wickets to win the T20 series",
        "Batter smashes century as team takes first innings lead in Ranji Trophy",
        "Football club signs striker ahead of the new season",
        "Athlete wins gold medal at the national championships",
        "Captain named for upcoming Test tour, selectors announce squad",
    ],
    "Entertainment": [
        "Actor's new film crosses Rs 100 crore at the box office",
        "Trailer of the upcoming movie released, fans react",
        "Singer announces concert tour across Indian cities",
        "Web series to stream on OTT platform next month",
        "Celebrity couple attends film premiere",
    ],
    "Science & Technology": [
        "ISRO successfully launches satellite into orbit",
        "Scientists discover new species and publish research findings",
        "Tech company unveils new smartphone with AI features",
        "Government plans rules for artificial intelligence and data privacy",
        "Researchers develop new technology at institute lab",
    ],
    "Environment & Weather": [
        "IMD issues heavy rain alert for several districts",
        "Air quality turns severe as pollution levels rise in the city",
        "Temperature drops as cold wave grips the state",
        "Tiger spotted in forest reserve, wildlife officials monitor",
        "Monsoon rainfall deficit raises climate concerns",
    ],
    "Disasters & Accidents": [
        "Five killed as bus falls into gorge in road accident",
        "Floods and landslides leave many dead, rescue operations underway",
        "Massive fire breaks out at factory, fire tenders rushed",
        "Building collapses after heavy rain, people trapped under debris",
        "Earthquake of magnitude 5 jolts the region",
    ],
    "Agriculture": [
        "Farmers demand better minimum support price for paddy",
        "Crop damage due to unseasonal rain worries farmers",
        "Government procures wheat from farmers at mandis",
        "Shortage of fertiliser hits farmers during sowing season",
        "Agriculture department promotes organic farming",
    ],
    "Infrastructure": [
        "Construction of new highway and flyover to begin next month",
        "Metro rail line inaugurated, commuters to benefit",
        "Railway station redevelopment project approved",
        "Residents complain of power cuts and poor water supply",
        "Government sanctions crore for road and bridge projects",
    ],
    "International": [
        "US President meets leaders at summit to discuss trade",
        "Russia and Ukraine continue talks amid ongoing war",
        "India and China hold talks on border issues",
        "United Nations calls for ceasefire in Gaza",
        "Pakistan and Bangladesh relations with India in focus",
    ],
}
