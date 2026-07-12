## 040
| Category | Aliases (code → header text) |
|---|---|
| Name | `name` |

## 307
| Category | Aliases (code → header text) |
|---|---|
| Name | `insured` → Insured |
| Sex | `sex` → Sex |
| DOB | `birthday` → Birthday |
| Policy # | `policynumber` → Policy Number |

## 416
| Category | Aliases (code → header text) |
|---|---|
| Name | `insname` → INS_NAME · `insnam` → INS_NAM · `nameofdeceased` → Name of deceased · `insuredname` → Insured Name |
| Sex | `sex` → SEX |
| DOB | `dob` → DOB |
| Policy # | `polnum` → POL_NUM · `policynumber` → Policy Number · `policyno` → Policy No |

## 462
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `name` → NAME · `nameofinsured` → Name of Insured · `cname` → CNAME · `nameofassured` → NAME OF ASSURED | claim sheets named "#1","#2" etc. extractable by VBA |
| Sex | `sex` → SEX · `cltsex` → CLTSEX | |
| DOB | `cltdob` → CLTDOB · `dob` → DOB · `dateofbirth` | |
| Policy # | `polnum` → POL_NUM · `policyno` → POLICY NO · `policynumber` → Policy Number · `chdrnum` → CHDRNUM | |

## 466
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `clinm` → cli_nm · `name` → Name · `nameofinsured` → Name of insured · `insuredname` → Insured Name · `firstnameandsurnameofinsured` → First name and surname of insured · `familyname` → family_name | `family_name` actually holds the full name; given_names col empty |
| Sex | `clisexcd` → cli_sex_cd · `sex` → Sex/sex | |
| DOB | `clibthdt` → cli_bth_dt · `dob` → DOB · `dateofbirth` → Date of Birth/date_of_birth | |
| Policy # | `polid` → pol_id · `policyno` → Policy No. · `policynumber` → Policy number/policy_number · `polno` → Pol no | |

## 476
| Category | Aliases (code → header text) |
|---|---|
| Name | `insured` → Insured |
| Sex | `sex` → Sex |
| DOB | `birthday` → Birthday |
| Policy # | `policynumber` → Policy Number · `policyno` → Policy No. |

## 479
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | — | No name column spotted |
| Sex | `sex` → Sex | |
| Policy # | `policynumber` → Policy Number / "Policy" | |

## 493
| Category | Aliases (code → header text) |
|---|---|
| Name | `cnames` → CNAMES · `insuredname` → Insured Name |
| First/Last | `insuredfirstname` → Insured_FirstName · `insuredlastname` → Insured_LastName |
| Sex | `sex` → SEX/Sex |
| DOB | `cltdob` → CLTDOB · `insuredbirthday` → Insured_birthday |
| Policy # | `chdrnum` → CHDRNUM · `policyno` → Policy No/Policy_NO |

## 497
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `name` → Name · `nameoflifeassured` → NAME_OF_LIFE_ASSURED · `laname` → LA Name | |
| Sex | `lifeassuredassuredsex` → Life Assured/Assured Sex · `sex` → SEX · `gender` → GENDER | |
| DOB | `lifeassuredassureddateofbirth` → Life Assured/Assured Date of Birth · `dateofbirth` → Date of Birth · `dob` → DOB · `ladob` → LA DOB | |
| Policy # | `policyno` → Policy No. · `policynumber` → Policy Number/POLICY NUMBER/POLICY_NUMBER | |
| Prem | `totalpremium` → TOTAL PREMIUM · `rigrossnetpremium` · `rinetpremiumamount` | Sheet: RGA Business (NPAR and PAR) |
| Prem | `ripremiumtotal` · `netripremium` | Sheet: Statement of Account |
| Claim | `finalclaimamount` · `claimamount` · `claimtype` | claimamount on Sheet Claim Recoveries |

## 499
| Category | Aliases (code → header text) |
|---|---|
| Name | `insname` → Ins Name · `insuredname` → Insured_Name |
| Sex | `insuredsex` → Insured SEX · `sex` → Sex |
| DOB | `dob` → DOB |
| Policy # | `policyno` → Policy No · `policynumber` → Policy Number/Policy_Number |

## 634
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `insured` → Insured · `name` → Name | |
| First/Last | `lastname` · `firstname` | |
| Sex | `sex` → sex/Sex | |
| DOB | `birthday` → birth_day · `dateofbirth` → Date of Birth | separate wrong-notation file also seen: birth_yr/birth_mon/birth_day |
| Policy # | `policyno` → policy_no/Policy No./Policy · `policynumber` → Policy Number/Number · `number` → Number | unmerged "[Policy]/[Number]" — "Number" is the safe identifier here |

## 659
| Category | Aliases (code → header text) |
|---|---|
| Name | `insname` → Ins_name/ins_name · `insured` → insured |
| First/Last | `lastname` · `firstname` |
| Sex | `sex` |
| DOB | `dob` |
| Policy # | `conno` → con_no · `policyno` → Policy No. |

## 676 (messy — face-sheet layout, not one-row header)
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `insured` → INSURED · `insuredname` → INSURED NAME · `lifeinsured` → Life Insured · `name` → NAME · `nameofassured` → Name of Assured · `surnamegivenname` → SURNAME + GIVEN_NAME · `nameofinsured` → NAME OF INSURED | |
| Sex | `sex` → SEX | |
| DOB | `dob` → DOB · `birthdate` → BIRTH DATE · `dateofbirth` → Date of Birth | |
| Policy # | `policyno` → POLICY NO · `polno` → POL NO · `policynumber` → POLICY NUMBER/Policy Number | |
| Prem | `netprem` → NET PREM · `total` (Ayala/Insular) · `totlifeprem`/`totprem` (Manulife) · `premiumfortheperiod` (Sunlife) | |
| Claim | `amountpaid`/`amountrecoverable` (Sunlife) · `totalcoverage`/`claimtype` (Manulife) · `causeofclaim`/`dateclaimpaid` (Sunlife) | |
| — | — | Claims/policy data appears as a hand-built summary block, not a clean header row — needs manual/VBA extraction |

## 679
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `nameofinsured` → NAME OF INSURED | |
| DOB | `birthdate` → BIRTH DATE | |
| Policy # | `policynumber` → POLICY NUMBER · `number` | file has "OUR POLICY NUMBER" vs "YOUR POLICY NUMBER" — "Number" alone is unsafe |
| Prem | `totalreinsurancepremium` · `total` (same row as name) | |

## 733 (large alias set — dual lowercase-key & literal-caption listings treated as one set)
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `assuredname`, `assuredowner`, `lifeassured`, `clientname`, `lassrd`, `clinm`, `completename`, `zlifname`, `familyname`, `insured`, `insuredname` (INSURED NAME), `laassuredname`, `laname`, `lifeassure`, `lifeassuredname`, `vlaname`, `lifeclientname`, `indcovered`, `claimantname`, `namela` |
| First/Last | `lastnameofclient`, `firstnameofclient`, `surname`, `givname` |
| Sex | `sex`, `gender`, `gendercode`, `cltsex`, `lagender`, `vlagender`, `clientsex`, `lasex`, `sexla` |
| DOB | `dob`, `birthdate`, `cltdob`, `dateofbirth`, `labirthday`, `ladob`, `dobtext`, `dladob`, `clientdateofbirth`, `ladateofbirth` |
| Policy # | `polno` (POLNO/POL_NO), `policynumber`, `policyno` (POLICY NO), `polnum`, `policy`, `contractno`, `chdrnum`, `contractnumber`, `contractnonew`, `certno`, `vpolicyno`, `vppno`, `polid` |
| Prem | Cedant-specific: `grosspremium`/`netpremium` (TM Asia), `totalriprem` (SG Retro MLRe), `grossprem`/`netprem`/`gp`/`np` (AIA Sch AI/AL), `retropremium` (Allianz), `reinsurancepremium` (AMAB), `grossprem`/`netprem`/`riprem` (AXA Affin), `totalprem` (CIMB Aviva), `ripremiumbeforegstrm`/`netprem` (Etiqa), `totalnetriprem`/`netprem` (GBSN), `totalriprem` (GE), `totalpremium`/`prem` (PRU/MLRe), `totalprem`/`netprem`/`riprem` (UniAsia) |
| Claim | `claimrecoveryamount`, `claimamount`, `claimsrecovery`, `cmclmamt`, `recoveryamt`, `nettpayment`, `retrossharerm`, `claimpayableamount`, `fullclaimamount`, `totalrirecoveryamountrm`, `revisedclaimamount`, `clmrecovery`, `claimid`, `totalclaimrecovery`, `finalclaimamount`, `claimstype`, `causeofevent`, `eventdate`, `causeofclaimremark`, `claimtype`, `dateofincident` |

## 740
| Category | Aliases (code → header text) |
|---|---|
| Name | `lassrd` → lassrd · `clientname` → Client Name |
| Sex | `sex` · `gender` → Gender |
| DOB | `dob` · `birthdate` → Birth Date |
| Policy # | `polno` · `policynumber` → Policy Number |
| Prem | `netriprem` |
| Claim | `totalclaimrecovery` · `claimcategorization` · `claimtype` |

## 749
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameofinsured` → Name of Insured |
| First/Last | `familyname` → Family Name · `givenname` → Given Name |
| Sex | `gender` → Gender |
| DOB | `dateofbirth` → Date Of Birth |
| Policy # | `policynumber` → Policy number/Policy Number |

## 770
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `laname`, `fullname`, `insuredname`, `applicantname`, `name`, `namaofinsured`, `nameofinsur`, `membname` | |
| First/Last | `familyname`, `givenname`, `firstname`, `lastname` | |
| Sex | `cedinggenderratebasis`, `gender`, `sex`, `insuredgender` | |
| DOB | `dateofbirth`, `dob` | |
| Policy # | `policynumber`, `policyno`, `policyref`, `polisno`, `policno` | |
| Prem | `grosspremi`/`netbalance` (ID) · `totannpremrm`/`riannpremrm`/`netripremrm` (MY) · `refundprem`/`reinspremi` (PH/TH) | |
| Claim | `dateofclaim` (ID/PH/TH) · `payableamt` (MY) · `liabilityinsurer`/`liabilityreas` (PH/TH) | |

## 832
| Category | Aliases (code → header text) |
|---|---|
| Name | `laname`, `name`, `policyholdername`, `assuredname`, `policyholder` |
| Sex | `sex` → SEX |
| DOB | `dob` → DOB · `birthdate` → BIRTH_DATE |
| Policy # | `polno`, `policyno`, `policy` |
| Prem | `grosspremium`, `netpremium`, `netriprem` |
| Claim | `claimamount` |

## 837
| Category | Aliases (code → header text) |
|---|---|
| Name | `lifeassdname` → Life Assd Name/LIFE_ASSD_NAME |
| Sex | `gender` → Gender |
| DOB | `dateofbirth` · `dob` |
| Policy # | `polno` → Pol-No/POL_NO |
| Prem | `feeamtriprem` · `erprem` — Bravo, CCA, FAC, Supreme Living Term |
| Claim | `netclaimamt` · `paymentamount` · `claimeventdate` |

## 898
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname` → INSURED_NAME |
| DOB | `dateofbirth` → DATE_of_BIRTH/Date of Birth |
| Policy # | `policynumber` → POLICY NUMBER · `cessionno` → CESSION_NO |

## 973
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `insuredname`, `surnamegivenname` |
| Sex | `sex`, `gender` |
| DOB | `dateofbirth`, `birthdate` |
| Policy # | `policyno`, `polno` |

## A03
| Category | Aliases (code → header text) |
|---|---|
| Name | `client` |
| Sex | `sex` → Sex |
| Policy # | `policy` → Policy |

## A88
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `name`, `insuredname` | |
| Sex | `sex` | |
| DOB | `dateofbirth`, `birth`, `dateof` | "Date of" alone unsafe — clashes with "Date of Event" |
| Policy # | `policynumber`, `policy`, `policyno`, `policyid` | "Policy" alone considered the safest identifier |
| Prem | `nettreins`, `reinstate`, `refund` | ID Retakaful |
| Claim | `rgashare`, `reasonof`, `diagnose`, `diagnosis`, `claimamount`, `claimno`, `claimtype` | |

## A94
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname` → Insured Name |
| Policy # | `pnumber` → Pnumber |

## B02
| Category | Aliases (code → header text) |
|---|---|
| Name | `clinm`, `insuredname`, `insured` |
| Sex | `sexcode`, `insuredgender`, `gender` |
| DOB | `birthdt`, `insuredbirthdate`, `birthdate` |
| Policy # | `polnum`, `policynumber` |
| Claim | `clamstatcode`, `clmrecvdt`, `claimtype`, `claimstatus` |
| Prem | `rgaripremium`, `transactiontype` |

## B03
| Category | Aliases (code → header text) |
|---|---|
| Name | `surnamegivenname`, `insuredname` |
| Sex | `sex` → SEX |
| DOB | `birthdate`, `dateofbirth` |
| Policy # | `polno`, `policyno` |
| Claim | `claimamount` |
| Prem | `necprem`, `totprem` |

## B08
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname`, `surnamegivenname`, `clientname`, `completename`, `clmant`, `insuredfullname` |
| First/Last | `givenname`, `familyname`, `mifinssurname`, `mifinsgivenname`, `rdrinssurname`, `rdrinsgivenname`, `lastname`, `firstname`, `midname` |
| Sex | `sex`, `gendercode`, `mifsex`, `rdrsex` |
| DOB | `birthdate`, `dateofbirth`, `dobdate`, `fibirthdate`, `mifbirthdate`, `rdrbirthdate`, `dob` |
| Policy # | `polno`, `policyno`, `policynumber`, `fipolno`, `mifpolicyno`, `rdrpolno`, `polnum` |
| Prem | `necprem`, `totprem` |
| Claim | `clmrecd`, `claimeventdate`, `clmno`, `clmaprovamt` |

## B09
| Category | Aliases (code → header text) |
|---|---|
| Name | `clientsname`, `insuredname`, `lifeassured`, `namaofinsured`, `nameofinsur`, `nameofinsured`, `insname`, `pname`, `surnamegivenname`, `policyowner`, `powner`, `owner`, `ownname`, `lifeinsured`, `life1`, `lifename`, `patient`, `namattg`, `lifeassuredname` |
| Sex | `sex`, `gender`, `inssex`, `sexcode` |
| DOB | `dob`, `dobofinsured`, `dateofbirth`, `birthdate`, `insdob`, `dateofbirthday`, `life1dob`, `tglahir` |
| Policy # | `policy`, `polnum`, `policynumber`, `policyno`, `polno`, `polis`, `polisno`, `policno`, `nopolis`, `participantno`, `nop` |
| Prem | `necbasicprm`/`totlifeprem` (Manulife) · `grosspremi`/`netbalance` (AXA Financial) · `netreinspremreindo` (AXA Mandiri) · `mdbtotprm` (Manulife Sch A) · `reinsurerprem`/`reinsurernetprem` (Prudential B&C) |
| Claim | `cededamount`/`reimamount`/`totalcoverage` (Manulife) · `claims` (AXA Financial) · `noclaim`/`amount` (AXA Mandiri) · `claim`, `claimreins`, `claimreason`, `causeofclaim`, `dateofdeath`, `claimpaid`, `deathdt`, `claimamountreinsurance`, `dateofadmission` |

## B19
| Category | Aliases (code → header text) |
|---|---|
| Name | `insname` → INS_NAME |
| Sex | `issuesex`, `sex` |
| Policy # | `polno`, `policyno` |

## B32
| Category | Aliases (code → header text) |
|---|---|
| Name | `fullname`, `insuredname`, `name`, `nameoftheinsureds`, `employeename` |
| First/Last | `firstname`, `lastname` |
| Sex | `gender`, `sex`, `sexoftheinsureds` |
| DOB | `birthdate`, `dateofbirth`, `dob`, `dateofbirthoftheinsureds` |
| Policy # | `persnum`, `policynumber`, `policyno` |

## B43
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `insname`, `insuredname` | |
| First/Last | `firstname`, `surname`, `firstnameeng`, `surnameeng` | |
| Sex | `sex` → SEX | |
| DOB | `birth`, `birthdate` | |
| Policy # | `polno`, `policyno` | |
| Prem | `prem` → PREM | |
| Claim | `payment`, `causeofdeath` | |
| — | — | Wrongly-merged header on Auto Re / Alteration Report — occurs on more than one sheet |

## B46
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `insuredname` | |
| First/Last | `first`, `last`, `firstname`, `lastname` | unmerged "[First]/[Last] [Name]/[Name]" — usable |
| Sex | `sex`, `gender` | |
| DOB | `bday`, `birthdate`, `dob`, `birthday`, `dateofbirth` | one sheet had blank first-row "[]/[Bday]" — unusable |
| Policy # | `policynumber`, `polnum`, `policyno` | "Policy" alone unsafe — clashes with "Policy Term" |
| Prem | `reinsurancepremium`, `rgapremium`, `natrepremium`, `total` | |
| Claim | `amount`, `claimtype`, `benefitpaid` | |

## B58
| Category | Aliases (code → header text) |
|---|---|
| First/Last | `inslastname` → INS1 LAST NAME · `insfirstname` → INS1 FIRST NAME |
| DOB | `insdob` → INS1 DOB |
| Policy # | `policynumber` → POLICY NUMBER |

## B60
| Category | Aliases (code → header text) |
|---|---|
| Name | `surnamegivenname`, `insuredname` |
| Sex | `sex` → SEX |
| DOB | `birthdate`, `dateofbirth` |
| Policy # | `polno`, `policyno` |
| Prem | `necbasicprm`, `totlifeprem`, `necprem`, `totprem`, `mdbprm`, `mdbtotprm`, `gapprem` |
| Claim | `claimtype`, `totalcoverage` |

## B67
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname` |
| Sex | `insuredsex`, `sex`, `insuredgender` |
| DOB | `insureddob`, `dob`, `insuresddob` |
| Policy # | `policyno` |

## C73
| Category | Aliases (code → header text) |
|---|---|
| Name | `enam` |
| Sex | `sex` |
| DOB | `birdat` |
| Policy # | `plcno` |

## D21
| Category | Aliases (code → header text) |
|---|---|
| Name | `clientname`, `name`, `clinm` |
| Sex | `clisex`, `sexcode`, `gender`, `sex`, `clisexcd` |
| DOB | `bthdt`, `birthdt`, `dateofbirth`, `clibthdt`, `dob` |
| Policy # | `polno`, `policyno`, `policynumber`, `polid` |
| Prem | `nrp` (SG), `nrpcrl` (TH) |
| Claim | `reinamount` (SG), `claimamount` (TH) |

## D59
| Category | Aliases (code → header text) |
|---|---|
| Name | `cnames`, `fullname` |
| First/Last | `surname`, `givname` |
| Sex | `cltsex`, `sex` |
| DOB | `cltdob`, `dob` |
| Policy # | `chdrnum`, `policynumber` |

## D72
| Category | Aliases (code → header text) |
|---|---|
| First/Last | `lastname` → LAST NAME · `firstname` → FIRST NAME |
| Policy # | `policy` → POLICY |

## E11
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `insuredname` |
| Sex | `sex` |
| DOB | `birth`, `birthdate` |
| Policy # | `polnum`, `policyno` |
| Prem | `annprem`, `modprem`, `premrga`, `premreindo`, `premmarein` |
| Claim | `causeofclaim`, `claimstatus` |

## E12
| Category | Aliases (code → header text) |
|---|---|
| Name | `lasname`, `laname` |
| Policy # | `policynumber`, `policycode` |
| Prem | `totalpremiumhan`, `totalpremiumrga` |
| Claim | `claimamountpaid`, `recoverablefromreinsurance`, `recoverablefromrga`, `recoverableamount` |

## E13
| Category | Aliases (code → header text) |
|---|---|
| Name | `fullname`, `clientname`, `issuedname` |
| Sex | `gender` |
| DOB | `dateofbirth`, `dob` |
| Policy # | `policyno`, `policynumber` |
| Prem | `basicripremium`, `ripremium`, `netbeforeclaims` |
| Claim | `grossclaimamount`, `recoveryamout` |

## E21
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `lifeassuredname` |
| Sex | `sex` |
| DOB | `birth` |
| Policy # | `polno` → POL_NO / "Pol no:" |
| Prem | `totalprem` |
| Claim | `reinsuredamount` |

## E45
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameofpersoninsured` |
| Sex | `sex` |
| DOB | `personinsureddob` |
| Policy # | `policyno` |

## E64
| Category | Aliases (code → header text) |
|---|---|
| DOB | `dob` |
| Sex | `sex` |
| Policy # | `policynumber` |

## E67
| Category | Aliases (code → header text) |
|---|---|
| Name | `name` |
| First/Last | `surname`, `name` |
| Sex | `sex`, `gender` |
| DOB | `dateofbirth` |
| Policy # | `certno`, `policyno` |
| Prem | `totalgross`, `netreinsurancepremium` |
| Claim | `claimamount` |

## E72
| Category | Aliases (code → header text) |
|---|---|
| Name | `cname`, `name`, `nameofinsured` |
| Sex | `cltsex`, `sex` |
| DOB | `cltdob`, `dob`, `dateofbirth` |
| Policy # | `chdrnum`, `polnum`, `policyno`, `policynumber` |

## G10
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameofinsured`, `name`, `insuredlifename`, `nameoflife` |
| First/Last | `firstname`, `lastname` |
| Sex | `sex`, `gender` |
| DOB | `pdob`, `birthdate`, `dateofbirth` |
| Policy # | `pno`, `polno`, `policyno`, `policynumber` |
| Prem | `riprem` (split RI SHARE/NAT RE SHARE), `annualreinsurancepremium`, `annprem` |
| Claim | `claimsamount`, `claimspayable` |

## G20
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameofinsured` |
| First/Last | `surname`, `givname` |
| Sex | `cltsex`, `gender` |
| DOB | `cltdob`, `dob` |
| Policy # | `chdrnum`, `policynotext` |
| Prem | `totalprem` (Gross Prem Billed), `totalripremrga`, `totalriprem` |
| Claim | `totalgrossamount`, `clmamt`, `claimsrecovery` |

## G26 (messy — path/tab text mixed into headers)
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `insuredname`, `name`, `nameoftheinsured` | |
| Sex | `sex`, `sexoftheinsured` | |
| DOB | `dateofbirth`, `dob`, `dateofbirthoftheinsured` | "Date of" alone unsafe — clashes with "Date of Death" |
| Policy # | `certificateno`, `certificate`, `policyno`, `policynumber` | "Policy" alone causes collisions (a "Policy Year" header also exists) |
| Prem | `reinsprem`, `totalreinspremium`, `nettreinspremium`, `reinstatenetpremium`, `netreinsurancepremium`, `reinsurancepremium` (Basic/Extra/Total), `nettreins` | |
| Claim | `claimamount`, `reasonof`, `rgashare`, `diagnose`, `causeofclaim` | 3 separate unmerged/wrongly-merged header issues logged for this company |

## G37
| Category | Aliases (code → header text) |
|---|---|
| Name | `iname`, `insured`, `insuredname`, `payorname`, `insurancedname` |
| Sex | `psex`, `sex` |
| DOB | `dob`, `birthdate`, `DoB` |
| Policy # | `ripno`, `policyno`, `policynumber` |
| Prem | `premium` (monthly), `netpremium` (FAC/HIS — different column from name), `xrxprm`/`totalpremi` (from ALI) |
| Claim | `claimamount` |

## G38
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `insuredname`, `namatertanggung`, `nameofinsured`, `pname`, `code2`, `holdername`, `owner`, `namapemegangpolis`, `patientname`, `policyowner` | `Code2` contains combined Name_DOB, e.g. "MANIUS HENDRI_19630429" |
| Sex | `sex`, `gender`, `sexcode` | |
| DOB | `dobofinsured`, `dob`, `dateofbirth`, `dateofbirthday`, `dobinsured` | |
| Policy # | `polnumall`, `policynumber`, `polnum`, `participantno`, `policyno`, `nopolis`, `polnumbertxt` | `polnum`/`polnumbertxt` duplicated-header issue |
| Prem | `rgagrossprem` (Trad/UL/MEP), `basicpremtotal`, `netreinspremrga`/`netreinspremrein`, `netreinsurancepremium` (CLP), `riprem` (Medicash/UL), `totalrgagrossprem`/`totalreindogrossprem` (MJP/UL), `premireas` (MSP/UL), `reindogrossprem`, `facpremium` (UL Kid) | |
| Claim | `totalclaims` (CLP), `reinsuranceclaim` (Trad), `riclaim` (UL), `claimstatus`, `claimtype`, `claimno`, `diagnosa` | |

## G39
| Category | Aliases (code → header text) |
|---|---|
| Name | `claimantname`, `name`, `clinm` |
| Sex | `sex` |
| DOB | `dob` |
| Policy # | `polno`, `policyno`, `polnum` |
| Prem | `cmnrppd` |
| Claim | `cmrecoam`, `claimcause`, `mlresshare`, `causeofevent`, `clmnum`, `claimantname` |

## H61
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname` |
| First/Last | `givname`, `surname` |
| Sex | `sex` |
| DOB | `birthdate` |
| Policy # | `policynumber`, `policynumbernew`, `policyno` |
| Prem | `repreamount` |
| Claim | `reclaimamount` (claim + prem on same sheet), `deathdate` |

## H62
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameofjointlifeassured` |
| Sex | `sex`, `gender` |
| DOB | `dateofbirth` |
| Policy # | `policynumber` |
| Prem | `totalgrosspremium`, `netamount` |
| Claim | `sumreinsured`, `reinsurersshare`, `claimtrid` |

## H79
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `namesurname`, `name` | |
| First/Last | `name` (NAME), `lastname`, `firstname`, `lastnameen`, `firstnameen` | |
| Sex | `gender`, `sex`, also a "RASEX" column mapped to sex | |
| DOB | `dateofbirth`, `dobyyymmdd`, `birthday`, `birthdate`, `birthdt` | Wrong-DOB-notation issue logged |
| Policy # | `policyno`, `policynumber`, `policy`, `cessionno`, `ponumas4010`/`ponumbas400` | |
| Prem | `grosspremium`, `netpremium`, `netreinsurancepremium` (Death/DIS/PD), `rmodepremium`, `premium`, `reinsurancepremium`, `ripremretotalperpol` | |
| Claim | `claimamount`, `totalmtlclaimamount`, `reinrecovery`, `causeofdeath`, `reinsurershare`, `grossclaimsamount` | |

## H88
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameoftheinsured`, `ciname` |
| First/Last | `cmfirstnm`, `cmlastnm` |
| Sex | `bpcustsex`, `sex` |
| DOB | `bpcustdob`, `dateofbirth`, `cdob` |
| Policy # | `prpolicyno` |
| Prem | `prriprem` |
| Claim | `ccclaimspaid` |

## I52
| Category | Aliases (code → header text) |
|---|---|
| Name | `namel`, `laname`, `personcovered`, `name`, `customername` |
| Sex | `sex`, `genderl`, `gender` |
| DOB | `ridob`, `dob`, `dobl`, `dateofbirth` |
| Policy # | `ricert`, `polno`, `certno`, `policynumber` |
| Prem | `totalpremium`, `netpremium`, `totprm`, `total`, `ripremtot`, `prem` |
| Claim | `claimamount`, `reinamt`, `claimity`, `finalclaimamount`, `totalclaim` |

## I94
| Category | Aliases (code → header text) |
|---|---|
| Name | `laassuredname`, `laname`, `lifeassuredname`, `completename`, `familyname` |
| Sex | `lagender`, `sex`, `gendercode` |
| DOB | `labirth`/`labirthday`, `dob`, `birthdate`, `dateofbirth` |
| Policy # | `policyno`, `contractno`, `policynumber` |
| Prem | `grosspremium`, `netpremium`, `riprem`, `totalpremium`, `netprem`, `totalprem`, `totalpremium1` — split across Banca Annual/Monthly, ILP Banca, AP IL/ILP products |
| Claim | `claimamount`, `revisedclaimamount`, `claimrecoveryamount`, `netclaimamount`, `claimpaiddate` |

## J53
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname` |
| Sex | `insuredgender` |
| DOB | `dob`, `insureddob` |
| Policy # | `policynumber`, `polnum` |
| Prem | `retotalprem`, `rgaprem` |
| Claim | `totalclaimbenefit` |

## K06
| Category | Aliases (code → header text) |
|---|---|
| Name | `membername`, `memname`, `personcoveredborrower` |
| Sex | `gender`, `memsex` |
| DOB | `memdob` |
| Policy # | `policyno`, `polno` |
| Prem | `totalpremium` |
| Claim | `claimamount`, `recoveryamount`, `claim` |

## K54
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `insurednamefull`, `insuredsname`, `name` | |
| First/Last | `cmfirstnm`, `cmlastnm` | |
| Sex | `gender`, `sex` | |
| DOB | `dateofbirthoftheinsured`, `dob` | Split into separate BirthYear/BirthMonth/BirthDay columns — wrong-notation issue |
| Policy # | `policynumber`, `prpolicyno` | |
| Prem | `bppremamt`, `prriprem` | |

## M19 (header not one-row — actuarial face-sheet + schedule)
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `nameofassured` |
| Sex | `sex`, `gender` |
| DOB | `dob` |
| Policy # | `policyno`, `polno` |
| Prem | `nrp` |
| Claim | `reinamount`, `claimdate`, `claimamount`, `claimtype`, `claimcause` |

## M35
| Category | Aliases (code → header text) |
|---|---|
| First/Last | `firstname`, `lastname` |
| Sex | `sex` |
| DOB | `dob` |
| Policy # | `policyno` |
| Prem | `netbalances` |
| Claim | `claimrecoveryamt`, `coverage` |

## M38
| Category | Aliases (code → header text) |
|---|---|
| Name | `clientsname`, `lifeassured`, `lifeinsured`, `lifeassuredname`, `lifenm` |
| Sex | `sex` |
| DOB | `dob`, `dateofbirth` |
| Policy # | `policy`, `polis`, `policyno`, `CHDRNUM`, "Policy #", "Polis #", `PolicyNo` |
| Prem | `netpremium`/`premium` (ID), `basicripremium`/`rgapremium` (Retakaful) |
| Claim | `claimpaid` (split IDR/USD, ID), `claim` (Retakaful), `claimreason` |

## M39
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `cpiname`, `nameinsured`, `nameoftheinsured`, `cpphname`, `insuredname` | This is the case where the tool couldn't auto-pick "Name of the insured" despite it being in the library — fixed 2020-06-01 |
| Sex | `cpicpsexcode`, `sex`, `sexoftheinsured`, `genderins` | |
| DOB | `cpbirthdate`, `dob`, `dateofbirthoftheinsured`, `dobinsured` | |
| Policy # | `prpolicyno`, `policynumber`, `policyno` | |
| Prem | `grossreinsprem`, `totalreinsprem`, `netreinsprem` | |
| Claim | `paidclaimsamount` | |

## M91
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `familyname`, `personcoveredsname`, `namepc`, `personcoveredsnaoe`, `naoepc` |
| Sex | `sex`, `gender`, `personcoveredsgender`, `sexpc` |
| DOB | `dateofbirth`, `dob`, `personcoveredsdob`, `dobpc` |
| Policy # | `contractno`, `contractnonew`, `polno`, `contrno` |
| Prem | `totalpremium` |
| Claim | `amountrecoverable`, `claimamount`, `aoountrecoverable` |

## N19
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredsname`, `name`, `rightname` |
| Sex | `gendercode`, `gender`, `insuredgender` |
| DOB | `dateofbirth`, `birthdate`, `birthday`, `insureddob`, `dob` |
| Policy # | `policynumber`, `polnumber`, `policycode`, `policyno`, `polcode`, `distinctpolno` |
| Prem | `totalprem` |
| Claim | `paymentamount`, `recoveries`, `claimsamount`, `causeofclaim` |

## N47
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `lifeassured` |
| Sex | `sex` |
| DOB | `dob` |
| Policy # | `polnum`, `policyno`, `newcertificateno` |
| Prem | `cmnrppd`, `netprem` |
| Claim | `claimsamount`, `recoverableamountrm`, `claimtype` |

## N96
| Category | Aliases (code → header text) |
|---|---|
| Prem | `amountofreinsurancepremiumsbeingpaid` — split Term Life / Acc TPD |

## N97
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname` |
| Sex | `sex` |
| DOB | `insureddateofbirth` |
| Policy # | `policynumber` |

## P06
| Category | Aliases (code → header text) |
|---|---|
| Name | `laname`, `participantname`, `clientname` |
| First/Last | `firstnameofclient`, `lastnameofclient` |
| Sex | `lasex`, `sex`, `gender` |
| DOB | `ladob`, `dateofbirth`, `birth` |
| Policy # | `polno`, `policyno`, `certificateno`, `policynumber` |
| Prem | `grossprem`, `netprem`, `totalprem` |
| Claim | `totalclaimrecoveries`, `netrecoveries`, `claim`, `claimno` |

## P07
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameofinsured`, `policyinsured` |
| Sex | `sex` |
| DOB | `dateofbirth`, `dob` |
| Policy # | `policynumber`, `policyid` |
| Prem | `reinspremium` |
| Claim | `claimincurred` |

## P56
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameoftheinsureds`, `nameofinsured`, `insuredname`, `primaryname`, `lifeassuredname` |
| Sex | `sexoftheinsureds`, `sex` |
| DOB | `doboftheinsureds`, `dob` |
| Policy # | `policynumber`, `policyid` |
| Prem | `reinsurancepremiumbeingpaid`, `reinstatedprem` |
| Claim | `originalamountpaiddhi`, `dateofclaimevent`, `causeofclaim` |

## P74 (header not one-row — face-sheet layout)
| Category | Aliases (code → header text) |
|---|---|
| Name | `lifeassured`, `nameofdeceased` |
| First/Last | `surname`, `firstname` |
| Sex | `sex` |
| DOB | `dateofbirth` |
| Policy # | `polno`, `policyno` |

## Q31
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameoftheinsured`, `name`, `insname`, `poname`, `nameofinsured`, `ainame`, `customername`, `issuedname`, `claimantname` |
| Sex | `sexoftheinsured`, `sex`, `sexofinsured`, `aisex`, `inssex`, `gender` |
| DOB | `dateofbirthoftheinsured`, `dobofinsured`, `dob`, `aibirdte`, `customerdob` |
| Policy # | `policynumber`, `polnum`, `aipolnum`, `policynum` |
| Prem | `totalamountofreinsurancepremiums`, `amountofreinsurancepremiumsbeingpaid`, `totalpremium` |
| Claim | `claimamount`, `clmamt` |

## Q37
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname` |
| Sex | `insuredgender`, `sexinsured`, `gender` |
| DOB | `insureddob`, `insdob`, `dobinsured` |
| Policy # | `policyno`, `polno`, `policynumber` |
| Prem | `rgareinsurancepremiumcontributioncoi`, `reinsurancepremiumcontributioncoi`, `nettreinsurancepremiumnettcontributionnettcoi`, `reinsurancenetpremiumrga` |
| Claim | `amountsubmit`, `amountapprove`, `paidclaimamountreinsurerrga`, `claimtype`, `netamountatriskgrossclaimsamounttmli`, `netamountatriskgrossclaimsamounttoreinsurer`, `claimref`, `claimamt`, `diagnosisdesc`, `claimamtpaidreinsurer` |

## Q47
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredsname` |
| Sex | `genderofinsured` |
| DOB | `dateofbirth`, `dateofbirthofinsured` |
| Policy # | `policynumber` |
| Prem | `reinsurancepremiums`, `natrepremiums`, `totalripremiums` |
| Claim | `coveredamountatthedateofclaim`, `finalclaimamount`, `claimamount`, `claimnumber` |

## Q72
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameofinsured`, `name`, `membername`, `customername` |
| Sex | `sex` |
| DOB | `birthdate`, `dateofbirth` |
| Policy # | `policynumber`, `policyno` |
| Prem | `grosspremium`, `netpremium` |
| Claim | `claimspaidamount` |

## Q74
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `firstnameandsurnameofinsured`, `fullname`, `givennames`, `clientname`, `clentname`, `name` | "given names" holds the full name; "family name" is empty |
| Sex | `sex`, `gender` | |
| DOB | `dateofbirth`, `birthday` | |
| Policy # | `policynumber`, `policyno` | |

## Q91
| Category | Aliases (code → header text) |
|---|---|
| Name | `name`, `clinm`, `clientname` |
| Sex | `sex`, `clisex` |
| DOB | `bthdt`, `dateofbirth` |
| Policy # | `policynumber`, `polno`, `polid` |
| Prem | `nrp`, `nrpcrl` |
| Claim | `claimamount`, `recoveryamount`, `claimamountrecovery` |

## Q93
| Category | Aliases (code → header text) |
|---|---|
| Name | `insnm`, `insname`, `insuredname`, `surnamegivenname`, `lifeassuredname` |
| First/Last | `firstname`, `lastname` |
| Sex | `sexcode`, `inssex`, `sex` |
| DOB | `insdob`, `birthdate`, `dateofbirth` |
| Policy # | `polnum`, `polno`, `policyno` |
| Prem | `mdbtotprm`, `gapprem` |
| Claim | `totalcoverage`, `reimamount` |

## Q99
| Category | Aliases (code → header text) |
|---|---|
| Name | `rinsnm`, `insuredname` |
| Sex | `rsex`, `sex` |
| DOB | `dob` |
| Policy # | `rpolno`, `policyno` |
| Prem | `rgaprem`, `netri`, `totripremnew`, `rrinet`, `totprem` |
| Claim | `totalamountofclaimpaidout`, `amountofclaimthecompanypaid`, `amountofclaimtoberecoveredfromreinsurer`, `claimamount`, `causedesc`, `clmpaymentdate`, `claimtype` |

## R29
No fields — legend row only, no data in this company's entry.

## R30
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `nameof`/`nameofinsured`/`name`/`membername` | unmerged "[NAME OF]/[INSURED]" |
| Sex | `sex` | |
| DOB | `birth`/`birthdate`/`dateofbirth` | unmerged "[BIRTH]/[DATE]" |
| Policy # | `policy`/`policynumber` | unmerged "[POLICY]/[NUMBER]" |
| Prem | `escireinsurancepremium` | |
| Claim | `claimspaidamount`, `reinsurer'sshareinclaims` | |
| — | — | 3-way unmerged header across Name/Sex/DOB/Policy on one sheet |

## R42
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredfullname`, `insuredname`, `policyholder`, `policyinsured` |
| Sex | `gender`, `sex` |
| DOB | `birthdate`, `dob` |
| Policy # | `mainpolno`, `certificateno` |
| Prem | `reinstotalpremium`, `reinsbalance`, `spctotalpremium`, `spcnettpremium` |
| Claim | `claimno`, `reinstotalclaim`, `causeofclaim`, `reinsclaim`, `claimdate`, `claimincurred` |

## R71
| Category | Aliases (code → header text) |
|---|---|
| Name | `laname`, `clientname` |
| Sex | `gender`, `lasex` |
| DOB | `dateofbirth`, `dob`, `clientdob` |
| Policy # | `polno`, `policyno` |
| Prem | `totalreprem`, `basicrepretotal`, `totalreprecyrt` |
| Claim | `recoverable`, `claimno` |

## R81
| Category | Aliases (code → header text) |
|---|---|
| Name | `insured` |
| Sex | `sex` |
| DOB | `birthday` |
| Policy # | `policynumber` |

## S08
| Category | Aliases (code → header text) |
|---|---|
| Name | `cpinsured`, `cppolicyholder`, `insuredname`, `nameinsureds` |
| Sex | `cpsexinsured`, `sex`, `sexoftheinsureds` |
| DOB | `cpdobinsured`, `dob`, `dateofbirthoftheinsureds` |
| Policy # | `policyno`, `policynumber` |

## S52
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredsname`, `lifeassured`, `PARTICIPANTS_NAME` |
| Sex | `sex` |
| DOB | `insuredsdob`, `dob` |
| Policy # | `policynumber` |
| Prem | `reinsurancepremium` |
| Claim | `paidamount`, `claim` |

## S54
| Category | Aliases (code → header text) | Notes |
|---|---|---|
| Name | `nameofinsured`, `insuredname`, `nameofassured`, `lifeinsured`, `lifeassuredname`, `namattg`, `lifename`/`lifenm`, `policyowner`, `clientsname`, `life1`/`life2`/`life3` | |
| Sex | `sexoftheinsured`, `sex` | |
| DOB | `dateofbirth`, `tglahir`, `dob`, `life1dob`/`life2dob`/`life3dob` | |
| Policy # | `polisno`, `nopolis`, `certno`, `policyno`, `chdrnum`, `polnum`, `policy` | "CERT. NO." used as the identifier over "POLICY NO." — same row as name |
| Prem | `contribpremi` | |
| Claim | `liabilityinsured`, `liabilityreinsured`, `causeofclaim`, `claim` | |

## S65
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredsname` |
| Sex | `genderofinsured` |
| DOB | `dateofbirthofinsured` |
| Policy # | `policynumber` |

## S72
| Category | Aliases (code → header text) |
|---|---|
| Name | `laassuredname`, `participantsname` |
| Sex | `lagender`, `participantsgender` |
| DOB | `labirthday`, `participantsbirthday` |
| Policy # | `certificateno`, `certno` |
| Prem | `prem`, `totalcontribution` |
| Claim | `totalclaim`, `revisedclaimamount` |

## S75
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredsname`, `lifeassured` |
| Sex | `sex` |
| DOB | `insuredsdob` |
| Policy # | `policynumber` |
| Prem | `reinsprem`, `ghoreinsprem`, `ghostdreinsprem` |
| Claim | `zcursumaclaim`, `apprvdamt` |

## S83
| Category | Aliases (code → header text) |
|---|---|
| Name | `lifeassdname` |
| Sex | `gender` |
| DOB | `dateofbirth` |
| Policy # | `polno` |

## S87
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname`, `insurednameoptional`, `name`, `lifeassuredname`, `nameoftheinsured`, `nameoftheinsureds` |
| First/Last | `firstname`, `lastname` |
| Sex | `sex`, `gender` |
| DOB | `dateofbirth`, `dob`, `dateofbirthoftheinsureds` |
| Policy # | `policyno`, `policynumber`, `polno` |
| Prem | `sumofripremium` |
| Claim | `claim`, `causeofclaim`, `diagnosis` |

## S94
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname`, `nameoftheinsured`, `surnamegivenname` |
| Sex | `sex` |
| DOB | `birthdate`, `dateofbirth` |
| Policy # | `polno`, `policyno`, `policynumber` |

## T87
| Category | Aliases (code → header text) |
|---|---|
| Sex | `genderofmainlife` |
| DOB | `dateofbirthofmainlife` |
| Policy # | `policynumber` |
| Prem | `totalgrossripremium`, `totalnetripremiumpayableinpolicycurrency`, `totalnetripremiumpayableinsgd` |
| Claim | `totalrirecoveriesreceivablefromreinsurer`, `claimamount` |

## T88
| Category | Aliases (code → header text) |
|---|---|
| Sex | `sex` |
| DOB | `birthdate` |
| Policy # | `policyno` |
| Prem | `premiumlife`, `premiumacc`, `premiumtpd`, `extrapremiumlife`, `extrapremiumacc`, `extrapremiumtpd`, `extapmlife`, `extapmacc`, `extapmtpd` |
| Claim | `reinslife`, `reinsacc`, `claimlife`, `claimacc` |

## U20
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameoftheinsureds` |
| Sex | `sexoftheinsureds` |
| DOB | `dateofbirthoftheinsureds` |
| Policy # | `policynumber` |
| Prem | `netamountatrisk`, `reinsurednetamountatrisk` |
| Claim | `reinsurershareinclaimsamount` |

## U27
| Category | Aliases (code → header text) |
|---|---|
| Name | `lifeassuredname`, `laname`, `clinm` |
| Sex | `gender`, `lagender`, `sexcode` |
| DOB | `dob`, `ladob`, `birthdt` |
| Policy # | `policynumber`, `polno`, `polnum` |
| Prem | `basereinspremdb`, `totalreinsprem` |
| Claim | `causeofclaim`, `claimtype` |

## U29
| Category | Aliases (code → header text) |
|---|---|
| Sex | `gender` |
| DOB | `dob` |
| Policy # | `policynumber` |
| Prem | `basereinspremdb` |

## U40
| Category | Aliases (code → header text) |
|---|---|
| Name | `lifeclientname`, `zlifname`, `laname`, `lifeassuredname`, `name` |
| Sex | `gender`, `clientsex`, `cltsex`, `sex` |
| DOB | `dob`, `clientdateofbirth`, `cltdob` |
| Policy # | `policynumber`, `contractnumber`, `chdrnum`, `polno` |
| Prem | `basereinspremdb` |
| Claim | `claimtype`, `claimnumber`, `claimno`, `causeofclaim`, `causeofclaimcode`, `claimreasons` |

## U54
| Category | Aliases (code → header text) |
|---|---|
| Name | `insuredname`, `insurednameoptional` |
| Sex | `sex`, `insuredgendercode` |
| DOB | `dateofbirth`, `insuredbirthdt`, `birthdate` |
| Policy # | `policyno`, `policyid` |
| Prem | `repremium` |
| Claim | `cedantpaid`, `causeofloss`, `cambodiaresshare` |

## W18
| Category | Aliases (code → header text) |
|---|---|
| Name | `nameoftheinsureds` |
| Sex | `sexoftheinsured` |
| DOB | `doboftheinsured` |
| Policy # | `policynumber` |
| Prem | `amountofreinsurancepremiumbeingpaid` |
| Claim | `grossclaimsamount`, `reinsurersshareinclaimsamount`, `incidentdate`, `causeofclaim`, `claimstatus` |

## W92
| Category | Aliases (code → header text) |
|---|---|
| Name | `lifeinsured` |
| Sex | `sex` |
| Policy # | `policyno` |
| Prem | `rga_netpremium`, `rga_premium` |
| Claim | `claimreason` |
