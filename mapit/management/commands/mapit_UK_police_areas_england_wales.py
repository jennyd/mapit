# "code" and "name" values were fetched from the Police API, data from which
# may be used under the terms of the Open Government Licence:
#
#     http://policeapi2.rkh.co.uk/api/docs/method/forces/
#
# The description of each police area here is taken from Schedule 1 to the
# Police Act 1996, taking account of subsequent amendments, including two
# changes (to Bedfordshire Police and Cheshire Constabulary) which are still
# outstanding in the online version:
#
#     http://www.legislation.gov.uk/ukpga/1996/16/schedule/1
#
# The legislation may be used under the terms of the Open Government Licence:
#
#     http://www.nationalarchives.gov.uk/doc/open-government-licence/
#
# Where the name of a district in the description does not match the lookup
# used, the reason for the discrepancy is given along with an official source,
# if possible (this is generally due to subsequent local government reforms).
#
# Many references for subsequent amendments and name changes were found in
# citations on Wikipedia.

police_areas = (
    # North West Somerset was renamed as North Somerset in either 1996 or 2005:
    #     http://www.legislation.gov.uk/uksi/1995/493/article/4/made
    #     http://www.n-somerset.gov.uk/cairo/docs/doc10520.htm
    # ...depending on whether or not the change was legally valid the first time:
    #     http://www.n-somerset.gov.uk/cairo/docs/doc10395.htm
    #       (section 3.5, Technical Issues from the 1996 Re-organisation)
    {"code": "avon-and-somerset",
     "name": "Avon and Somerset Constabulary",
     "description": """The county of Somerset and the non-metropolitan
                districts of Bath and North East Somerset, Bristol,
                North West Somerset and South Gloucestershire""",
     "lookup": (("CTY", "Somerset"),
                ("UTA", "Bath and North East Somerset"),
                ("UTA", "Bristol"),
                ("UTA", "North Somerset"),
                ("UTA", "South Gloucestershire"))},
    # Bedfordshire is amended by S.I. 2009/119 art. 3 (change still outstanding):
    #     http://www.legislation.gov.uk/uksi/2009/119/article/3/made
    # 'Bedford ' has a trailing space to prevent it also matching 'Bedfordshire'
    {"code": "bedfordshire",
     "name": "Bedfordshire Police",
     "description": """The non-metropolitan districts of Bedford,
                Central Bedfordshire and Luton""",
     "lookup": (("UTA", "Bedford "),
                ("UTA", "Central Bedfordshire"),
                ("UTA", "Luton"))},
    {"code": "cambridgeshire",
     "name": "Cambridgeshire Constabulary",
     "description": """The county of Cambridgeshire and the
                non-metropolitan district of Peterborough""",
     "lookup": (("CTY", "Cambridgeshire"),
                ("UTA", "Peterborough"))},
    # Cheshire is amended by S.I. 2009/119 art. 6 (change still outstanding):
    #     http://www.legislation.gov.uk/uksi/2009/119/article/6/made
    {"code": "cheshire",
     "name": "Cheshire Constabulary",
     "description": """The non-metropolitan districts of Cheshire East,
                Cheshire West and Chester, Halton and Warrington""",
     "lookup": (("UTA", "Cheshire East"),
                ("UTA", "Cheshire West and Chester"),
                ("UTA", "Halton"),
                ("UTA", "Warrington"))},
    # FIXME Find the City of London Police Act 1839, which defines the force
    # area:
    #     http://www.cityoflondon.gov.uk/about-the-city/who-we-are/police-authority/Pages/default.aspx
    # Inner and Middle Temples are excluded from the Metropolitan police area
    # along with the City of London. They appear to be within the City of London
    # police area in practice, although I haven't been able to find any
    # legislative basis for that.
    {"code": "city-of-london",
     "name": "City of London Police",
     "description": "",
     # override name is 'City of London Corporation'
     "lookup": (("LBO", "City and County of the City of London"),)},
    {"code": "cleveland",
     "name": "Cleveland Police",
     "description": """The non-metropolitan districts of Hartlepool,
                Middlesbrough, Redcar and Cleveland and Stockton-on-Tees""",
     "lookup": (("UTA", "Hartlepool"),
                ("UTA", "Middlesbrough"),
                ("UTA", "Redcar and Cleveland"),
                ("UTA", "Stockton-on-Tees"))},
    {"code": "cumbria",
     "name": "Cumbria Constabulary",
     "description": "The county of Cumbria",
     "lookup": (("CTY", "Cumbria"),)},
    {"code": "derbyshire",
     "name": "Derbyshire Constabulary",
     "description": """The county of Derbyshire and the non-metropolitan
                district of Derby""",
     "lookup": (("CTY", "Derbyshire"),
                ("UTA", "Derby"))},
    # Cornwall County Council was made a unitary authority in 2009 by S.I. 2008/491:
    #     http://www.legislation.gov.uk/uksi/2008/491/introduction/made
    {"code": "devon-and-cornwall",
     "name": "Devon & Cornwall Police",
     "description": """The counties of Devon and Cornwall, the
                non-metropolitan districts of Plymouth and Torbay and the
                Isles of Scilly""",
     "lookup": (("CTY", "Devon"),
                ("UTA", "Cornwall"),
                ("UTA", "Plymouth"),
                ("UTA", "Torbay"),
                ("COI", "Isles of Scilly"))},
    {"code": "dorset",
     "name": "Dorset Police",
     "description": """The county of Dorset and the non-metropolitan
                districts of Bournemouth and Poole""",
     "lookup": (("CTY", "Dorset"),
                ("UTA", "Bournemouth"),
                ("UTA", "Poole"))},
    # Durham County Council was made a unitary authority in 2009 by S.I. 2008/493:
    #     http://www.legislation.gov.uk/uksi/2008/493/introduction/made
    {"code": "durham",
     "name": "Durham Constabulary",
     "description": """The county of Durham and the non-metropolitan
                district of Darlington""",
     "lookup": (("UTA", "County Durham"),
                ("UTA", "Darlington"))},
    # Local authorities in Wales are all unitary authorities:
    {"code": "dyfed-powys",
     "name": "Dyfed Powys Police",
     "description": """The counties of Ceredigion, Carmarthenshire,
                Pembrokeshire and Powys""",
     "lookup": (("UTA", "Ceredigion"),
                ("UTA", "Carmarthenshire"),
                ("UTA", "Pembrokeshire"),
                ("UTA", "Powys"))},
    {"code": "essex",
     "name": "Essex Police",
     "description": """The county of Essex and the non-metropolitan
                districts of Southend-on-Sea and Thurrock""",
     "lookup": (("CTY", "Essex"),
                ("UTA", "Southend-on-Sea"),
                ("UTA", "Thurrock"))},
    {"code": "gloucestershire",
     "name": "Gloucestershire Constabulary",
     "description": "The county of Gloucestershire",
     "lookup": (("CTY", "Gloucestershire"),)},
    {"code": "greater-manchester",
     "name": "Greater Manchester Police",
     "description": """The metropolitan districts of Bolton, Bury,
                Manchester, Oldham, Rochdale, Salford, Stockport, Tameside,
                Trafford and Wigan""",
     "lookup": (("MTD", "Bolton"),
                ("MTD", "Bury"),
                ("MTD", "Manchester"),
                ("MTD", "Oldham"),
                ("MTD", "Rochdale"),
                ("MTD", "Salford"),
                ("MTD", "Stockport"),
                ("MTD", "Tameside"),
                ("MTD", "Trafford"),
                ("MTD", "Wigan"))},
    {"code": "gwent",
     "name": "Gwent Police",
     "description": """The county of Monmouthshire and the county boroughs
                of Blaenau Gwent, Caerphilly, Newport and Torfaen""",
     "lookup": (("UTA", "Monmouthshire"),
                ("UTA", "Blaenau Gwent"),
                ("UTA", "Caerphilly"),
                ("UTA", "Newport"),
                ("UTA", "Torfaen"))},
    # The Isle of Wight Council was made a unitary authority in 1995 by
    # S.I. 1994/1210:
    #     http://www.legislation.gov.uk/uksi/1994/1210/article/3/made
    {"code": "hampshire",
     "name": "Hampshire Constabulary",
     "description": """The counties of Hampshire and Isle of Wight and the
                non-metropolitan districts of Portsmouth and Southampton""",
     "lookup": (("CTY", "Hampshire"),
                ("UTA", "Isle of Wight"),
                ("UTA", "Portsmouth"),
                ("UTA", "Southampton"))},
    {"code": "hertfordshire",
     "name": "Hertfordshire Constabulary",
     "description": "The county of Hertfordshire",
     "lookup": (("CTY", "Hertfordshire"),)},
    {"code": "humberside",
     "name": "Humberside Police",
     "description": """The non-metropolitan districts of the East Riding of
                Yorkshire, Kingston upon Hull, North East Lincolnshire and
                North Lincolnshire""",
     "lookup": (("UTA", "East Riding of Yorkshire"),
                ("UTA", "Kingston upon Hull"),
                ("UTA", "North East Lincolnshire"),
                ("UTA", "North Lincolnshire"))},
    # Medway Towns is still officially referred to as such rather than just
    # 'Medway', e.g.:
    #     http://www.legislation.gov.uk/uksi/2012/1803/schedule/crossheading/local-government/made
    # However, the council calls itself 'Medway Council':
    #     http://www.medway.gov.uk/councilanddemocracy/aboutus.aspx
    {"code": "kent",
     "name": "Kent Police",
     "description": """The county of Kent and the non-metropolitan district
                of Medway Towns""",
     "lookup": (("CTY", "Kent"),
                ("UTA", "Medway"))},
    {"code": "lancashire",
     "name": "Lancashire Constabulary",
     "description": """The county of Lancashire and the non-metropolitan
                districts of Blackburn with Darwen and Blackpool""",
     "lookup": (("CTY", "Lancashire"),
                ("UTA", "Blackburn with Darwen"),
                ("UTA", "Blackpool"))},
    {"code": "leicestershire",
     "name": "Leicestershire Police",
     "description": """The county of Leicestershire and the non-metropolitan
                districts of Leicester and Rutland""",
     "lookup": (("CTY", "Leicestershire"),
                ("UTA", "Leicester"),
                ("UTA", "Rutland"))},
    {"code": "lincolnshire",
     "name": "Lincolnshire Police",
     "description": "The county of Lincolnshire",
     "lookup": (("CTY", "Lincolnshire"),)},
    {"code": "merseyside",
     "name": "Merseyside Police",
     "description": """The metropolitan districts of Knowsley, Liverpool,
                St. Helens, Sefton and Wirral""",
     "lookup": (("MTD", "Knowsley"),
                ("MTD", "Liverpool"),
                ("MTD", "St. Helens"),
                ("MTD", "Sefton"),
                ("MTD", "Wirral"))},
    # The Greater London Authority Act 1999 amends the force area:
    #     http://www.legislation.gov.uk/ukpga/1999/29/section/323
    # Inner and Middle Temples appear to be within the City of London police
    # area in practice (although I haven't been able to find any legislative
    # basis for that).
    {"code": "metropolitan",
     "name": "Metropolitan Police Service",
     "description": """Greater London, excluding the City of London,
                the Inner Temple and the Middle Temple""",
     # This lookup is the empty list because we're treating this area as a
     # special case, and using all London boroughs except the City of
     # London:
     "lookup": []},
    {"code": "norfolk",
     "name": "Norfolk Constabulary",
     "description": "The county of Norfolk",
     "lookup": (("CTY", "Norfolk"),)},
    {"code": "northamptonshire",
     "name": "Northamptonshire Police Force",
     "description": "The county of Northamptonshire",
     "lookup": (("CTY", "Northamptonshire"),)},
    # Northumberland County Council was made a unitary authority in 2009 by
    # S.I. 2008/494:
    #     http://www.legislation.gov.uk/uksi/2008/494/introduction/made
    {"code": "northumbria",
     "name": "Northumbria Police",
     "description": """The county of Northumberland and the metropolitan
                districts of Gateshead, Newcastle upon Tyne, North Tyneside,
                South Tyneside and Sunderland""",
     "lookup": (("UTA", "Northumberland"),
                ("MTD", "Gateshead"),
                ("MTD", "Newcastle upon Tyne"),
                ("MTD", "North Tyneside"),
                ("MTD", "South Tyneside"),
                ("MTD", "Sunderland"))},
    {"code": "north-wales",
     "name": "North Wales Police",
     "description": """The counties of the Isle of Anglesey, Gwynedd,
                Denbighshire and Flintshire and the county boroughs of Conwy
                and Wrexham""",
     "lookup": (("UTA", "Isle of Anglesey"),
                ("UTA", "Gwynedd"),
                ("UTA", "Denbighshire"),
                ("UTA", "Flintshire"),
                ("UTA", "Conwy"),
                ("UTA", "Wrexham"))},
    # 'York ' has a trailing space to prevent it also matching 'Yorkshire'
    {"code": "north-yorkshire",
     "name": "North Yorkshire Police",
     "description": """The county of North Yorkshire and the
                non-metropolitan district of York""",
     "lookup": (("CTY", "North Yorkshire"),
                ("UTA", "York "))},
    {"code": "nottinghamshire",
     "name": "Nottinghamshire Police",
     "description": """The county of Nottinghamshire and the
                non-metropolitan district of Nottingham""",
     "lookup": (("CTY", "Nottinghamshire"),
                ("UTA", "Nottingham"))},
    # Rhondda, Cynon and Taff were merged in 1996 by the Local Government
    # (Wales) Act 1994 to form Rhondda Cynon Taf:
    #     http://www.legislation.gov.uk/ukpga/1994/19/schedule/1
    {"code": "south-wales",
     "name": "South Wales Police",
     "description": """The counties of Cardiff and Swansea and the county
                 boroughs of Bridgend, Merthyr Tydfil, Neath Port Talbot,
                 Rhondda, Cynon, Taff and the Vale of Glamorgan""",
     "lookup": (("UTA", "Cardiff"),
                ("UTA", "Swansea"),
                ("UTA", "Bridgend"),
                ("UTA", "Merthyr Tydfil"),
                ("UTA", "Neath Port Talbot"),
                ("UTA", "Rhondda Cynon Taf"),
                ("UTA", "Vale of Glamorgan"))},
    {"code": "south-yorkshire",
     "name": "South Yorkshire Police",
     "description": """The metropolitan districts of Barnsley, Doncaster,
                Rotherham and Sheffield""",
     "lookup": (("MTD", "Barnsley"),
                ("MTD", "Doncaster"),
                ("MTD", "Rotherham"),
                ("MTD", "Sheffield"))},
    {"code": "staffordshire",
     "name": "Staffordshire Police",
     "description": """The county of Staffordshire and the
                non-metropolitan district of Stoke-on-Trent""",
     "lookup": (("CTY", "Staffordshire"),
                ("UTA", "Stoke-on-Trent"))},
    {"code": "suffolk",
     "name": "Suffolk Constabulary",
     "description": "The county of Suffolk",
     "lookup": (("CTY", "Suffolk"),)},
    {"code": "surrey",
     "name": "Surrey Police",
     "description": "The county of Surrey",
     "lookup": (("CTY", "Surrey"),)},
    {"code": "sussex",
     "name": "Sussex Police",
     "description": """The counties of East Sussex and West Sussex and the
                non-metropolitan district of Brighton and Hove""",
     "lookup": (("CTY", "East Sussex"),
                ("CTY", "West Sussex"),
                ("UTA", "Brighton and Hove"))},
    # Berkshire County Council was dissolved in 1998 by S.I. 1996/1879 and its
    # functions transferred to six of its district councils as unitary authorities:
    #     http://www.legislation.gov.uk/uksi/1996/1879/article/3/made
    {"code": "thames-valley",
     "name": "Thames Valley Police",
     "description": """The counties of Berkshire, Buckinghamshire and
                Oxfordshire and the non-metropolitan district of
                Milton Keynes""",
     "lookup": (("UTA", "Bracknell Forest"),
                ("UTA", "Reading"),
                ("UTA", "Slough"),
                ("UTA", "West Berkshire"),
                ("UTA", "Windsor and Maidenhead"),
                ("UTA", "Wokingham"),
                ("CTY", "Buckinghamshire"),
                ("CTY", "Oxfordshire"),
                ("UTA", "Milton Keynes"))},
    {"code": "warwickshire",
     "name": "Warwickshire Police",
     "description": "The county of Warwickshire",
     "lookup": (("CTY", "Warwickshire"),)},
    # Shropshire County Council was made a unitary authority in 2009 by
    # S.I. 2008/492:
    #     http://www.legislation.gov.uk/uksi/2008/492/introduction/made
    # The Wrekin was renamed "Telford and Wrekin" in 1998, when the district
    # became a unitary authority. The only legislative reference I can find to
    # this change is in the footnote to S.I. 2002/2373 art.3:
    #     http://www.legislation.gov.uk/uksi/2002/2373/article/3/made
    {"code": "west-mercia",
     "name": "West Mercia Police",
     "description": """The counties of Shropshire and Worcestershire and
                the non-metropolitan districts of Herefordshire and
                The Wrekin""",
     "lookup": (("UTA", "Shropshire"),
                ("CTY", "Worcestershire"),
                ("UTA", "Herefordshire"),
                ("UTA", "Telford and Wrekin"))},
    {"code": "west-midlands",
     "name": "West Midlands Police",
     "description": """The metropolitan districts of Birmingham, Coventry,
                Dudley, Sandwell, Solihull, Walsall and Wolverhampton""",
     "lookup": (("MTD", "Birmingham"),
                ("MTD", "Coventry"),
                ("MTD", "Dudley"),
                ("MTD", "Sandwell"),
                ("MTD", "Solihull"),
                ("MTD", "Walsall"),
                ("MTD", "Wolverhampton"))},
    {"code": "west-yorkshire",
     "name": "West Yorkshire Police",
     "description": """The metropolitan districts of Bradford, Calderdale,
                Kirklees, Leeds and Wakefield""",
     "lookup": (("MTD", "Bradford"),
                ("MTD", "Calderdale"),
                ("MTD", "Kirklees"),
                ("MTD", "Leeds"),
                ("MTD", "Wakefield"))},
    # Wiltshire County Council was made a unitary authority in 2009 by
    # S.I. 2008/490:
    #     http://www.legislation.gov.uk/uksi/2008/490/introduction/made
    # Thamesdown was renamed as "Swindon" in 1997, shortly after it became a
    # unitary authority; I can't find any other source for this date:
    #     http://en.wikipedia.org/wiki/Thamesdown
    {"code": "wiltshire",
     "name": "Wiltshire Police",
     "description": """The county of Wiltshire and the non-metropolitan
                district of Thamesdown""",
     "lookup": (("UTA", "Wiltshire"),
                ("UTA", "Swindon"))}
)

