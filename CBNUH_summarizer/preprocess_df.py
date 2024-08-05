import copy
import re
import pandas as pd

class ExcelProcessor:
    def __init__(self, summarizer):
        self.summarizer = summarizer
        self.ANTIBIO_LIST = ['Amikacin', 'AmoxicillinClavulanic', 'AmpicillinSulbactam', 'Aztreonam', 'Cefazolin', 'Cefepime', 'Cefotaxime', 'Cefoxitin', 'Ceftazidime', 'Ciprofloxacin', 'Colistin', 'Ertapenem', 'ESBL', 'Gentamicin', 'Imipenem', 'Piperacillin', 'PiperacillinTazobactam', 'Tigecycline', 'TicarcillinClavulanic', 'TrimethoprimSulfamethoxazole', 'Gentamicin', 'Imipenem', 'Meropenem', 'Minocycline', 'Piperacillin', 'PiperacillinTazobactam', 'Benzylpenicillin', 'Ciprofloxacin', 'Clindamycin', 'Erythromycin', 'Fusidic', 'Gentamicin', 'Habekacin', 'Linezolid', 'Mupirocin', 'Nitrofurantoin', 'Oxacillin', 'Quinupristin', 'Rifampicin', 'Teicoplanin', 'Telithromycin', 'Tetracycline', 'Tigecycline', 'Vancomycin']
        self.antibiotics_list = ['OX', 'OX.1', 'FOXS', 'VA', 'VRS', 'ESBL', 'IPM', 'CL', 'AMC', 'ATM', 'CZ', 'FEP', 'CTX', 'CTX.1', 'FOX', 'MEM', 'PIP', 'TZP', 'TIC', 'TIM', 'ISP', 'MI', 'NET', 'TOB', 'AM', 'AM.1', 'CIP', 'GM', 'SXT', 'P-G', 'CC', 'E', 'LNZ', 'MXF', 'NIT', 'NOR', 'QDA', 'TE', 'FA', 'HAB', 'RIF', 'SAM', 'HLG', 'HLK', 'HLS', 'CRO', 'CF', 'C', 'ERT', 'TIG']
        self.antibiotic_summary = {
            'Amikacin': 'AM', 'Amoxicillin/Clavulanic': 'AMC', 'Ampicillin': 'AM.1', 'ESBL': 'ESBL', 'Imipenem': 'IPM', 'Tigecycline': 'TIG', 'Vancomycin': 'VA', 'Ampicillin/Sulbactam': 'SAM', 'Trimethoprim/Sulfamethoxazole': 'SXT', 'Gentamicin': 'GM', 'Ciprofloxacin': 'CIP', 'Minocycline': 'MI', 'Meropenem': 'MEM', 'Cefepime': 'FEP', 'Ceftazidime': 'CTX', 'Cefotaxime': 'CTX.1', 'Piperacillin/Tazobactam': 'TZP', 'Piperacillin': 'PIP', 'Ticarcillin/Clavulanic': 'TIM', 'Colistin': 'CL', 'Aztreonam': 'ATM', 'Ertapenem': 'ERT', 'Cefoxitin': 'FOX', 'Cefazolin': 'CZ', 'Chloramphenicol': 'C', 'Tetracycline': 'TE', 'Benzylpenicillin': 'P-G', 'Clindamycin': 'CC', 'Linezolid': 'LNZ', 'Oxacillin': 'OX.1', 'Nitrofurantoin': 'NIT', 'Quinupristin/Dalfopristin': 'QDA', 'Fusidic': 'FA', 'Habekacin': 'HAB', 'Rifampicin': 'RIF', 'Erythromycin': 'E', 'Tobramycin': 'TOB', 'Netilmicin': 'NET', 'Moxifloxacin': 'MXF', 'Ceftriaxone': 'CRO', 'Norfloxacin': 'NOR'
        }
        self.ANTIBIO_DICT = {antibiotic: [] for antibiotic in self.antibiotics_list}

    def process_file(self,file):
        data_file = file
        new_df = []
        total_ml_result = []

        for idx, row in data_file.iterrows():
            check_patient = row['감시대상자']
            sex = row['성별']
            birth = row['생년월일']
            blood_drawing = row['채혈일']
            check_in = row['접수일']
            read_day = row['판독일']
            hospitalization = row['입원일']
            colony = row['집락']
            examine_label = row['검사구분']
            specimen = row['검체명']
            summary = row['결과']
            original_text = row['검사결과']

            if isinstance(original_text, float):
                continue
            elif '동정결과' not in original_text:
                summary_text = self.summarizer(original_text, max_new_tokens=2000)[0]['summary_text']
                identification_code = None
                identification_result = None
                total_ml = None

                new_df.append([check_patient, sex, birth, blood_drawing, check_in, read_day, hospitalization, colony,
                               examine_label, specimen, summary, identification_result, total_ml] + [None] * len(self.antibiotics_list))
            else:
                original_text = original_text.replace('동정결과[중간보고]', '[중간보고]').replace('동정결과T', 'T')
                original_text_list = ['동정결과' + k if k[:6] != '[최종보고]' else 'pass' for k in list(
                    filter(None, original_text.strip().split('동정결과'))) if k[:6] != '[최종보고]']
                for origin in original_text_list:
                    antibiotic_results = copy.deepcopy(self.ANTIBIO_DICT)
                    summary_text = self.summarizer(origin, max_new_tokens=2000)[0]['summary_text']
                    antibiotic_list = summary_text.split(',')
                    compose_len = len(antibiotic_list)
                    identification_result = antibiotic_list[0].replace('동정결과', '').strip()
                    if compose_len == 1:
                        total_ml = None
                    else:
                        if '정도' not in antibiotic_list[1]:
                            total_ml = None
                            step_size = 1
                        else:
                            total_ml = antibiotic_list[1].replace("정도", "").replace('/ml', '').strip().replace(' ', '')
                            step_size = 2
                        check_same = []
                        for idx, antibiotic in enumerate(antibiotic_list[step_size:]):
                            if antibiotic in self.antibiotic_summary.keys():
                                if antibiotic not in check_same:
                                    check_same.append(antibiotic)
                                else:
                                    continue

                                antibiotic = self.antibiotic_summary[antibiotic]
                                try:
                                    if re.sub(r'(\()([a-zA-Z\+\-])(\))', r'\2', antibiotic_list[step_size + idx + 1].strip()) in ['S', 'R', 'I', '+', '-']:
                                        antibiotic_results[antibiotic].append(re.sub(r'(\()([a-zA-Z\+\-])(\))', r'\2', antibiotic_list[step_size + idx + 1].strip()))
                                except:
                                    print(antibiotic_list)

                    total_ml_result.append(total_ml)
                    for check in antibiotic_results.keys():
                        if len(total_ml_result) != len(antibiotic_results[check]):
                            antibiotic_results[check].append(None)
                    an_list = []
                    for an in antibiotic_results.values():
                        an_list.append(an[0])
                    new_df.append([check_patient, sex, birth, blood_drawing, check_in, read_day, hospitalization, colony,
                                   examine_label, specimen, summary, identification_result, total_ml] + an_list)

        new_df = pd.DataFrame(new_df, columns=data_file.columns[:-1].to_list() + ['동정결과', 'CLNYCN'] + self.antibiotics_list)
        return new_df