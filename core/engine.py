"""
Engine Module — Forward Chaining + Certainty Factor
====================================================
Two-phase diagnosis engine for baby disease expert system.

Phase 1: Forward Chaining
    Evaluate logical rules (AND/OR conditions from rules_forward.csv)
    to determine which diseases are triggered by the selected symptoms.

Phase 2: Certainty Factor
    For triggered diseases, calculate CF using rules_cf.csv weights.
    CF Combination Formula:
        CF_combine(CF1, CF2) = CF1 + CF2 * (1 - CF1)

CRITICAL: The mathematical logic below is verified and MUST NOT be altered.
"""

import re


def get_related_symptoms(selected_gejala, rules_fc_df, penyakit_df, gejala_df):
    """
    Find symptoms related to the currently selected ones via forward chaining rules.

    Scans all FC rules for any rule that contains at least one of the selected
    symptoms. Returns the OTHER symptoms from those rules (the ones not yet
    selected) as suggestions, grouped by the disease they point to.

    Parameters
    ----------
    selected_gejala : list
        Currently selected symptom IDs
    rules_fc_df : pd.DataFrame
        Forward chaining rules
    penyakit_df : pd.DataFrame
        Disease data for name lookups
    gejala_df : pd.DataFrame
        Symptom data for name lookups

    Returns
    -------
    list[dict]
        Sorted list of suggestion groups (most matched first). Each dict:
        - id_penyakit, nama_penyakit
        - suggested_symptoms: list of {id_gejala, nama_gejala, from_rules}
        - matched_count: how many selected symptoms appear in this disease's rules
        - total_needed: total unique symptoms across all rules for this disease
        - completion_pct: percentage of rule completion
    """
    if not selected_gejala:
        return []

    selected_set = set(selected_gejala)
    gejala_lookup = dict(zip(gejala_df['id_gejala'], gejala_df['nama_gejala']))
    penyakit_lookup = dict(zip(penyakit_df['id_penyakit'], penyakit_df['nama_penyakit']))

    # Track: disease -> { symptom_id -> [rule_ids that mention it] }
    disease_suggestions = {}  # id_penyakit -> {'suggested': {gid: [rules]}, 'matched': set}

    for _, rule in rules_fc_df.iterrows():
        rule_id = rule['id_rule']
        condition_str = rule['kondisi_if']
        penyakit_id = rule['id_penyakit']

        parsed = _parse_condition(condition_str)
        rule_symptoms = set(parsed['symptoms'])

        # Check if ANY of the selected symptoms appear in this rule
        overlap = rule_symptoms & selected_set
        if not overlap:
            continue

        # Initialize disease entry
        if penyakit_id not in disease_suggestions:
            disease_suggestions[penyakit_id] = {
                'suggested': {},  # gid -> [rule_ids]
                'matched': set(),
                'all_symptoms': set(),
            }

        disease_suggestions[penyakit_id]['matched'].update(overlap)
        disease_suggestions[penyakit_id]['all_symptoms'].update(rule_symptoms)

        # Find symptoms in this rule that are NOT yet selected -> suggestions
        missing = rule_symptoms - selected_set
        for gid in missing:
            if gid not in disease_suggestions[penyakit_id]['suggested']:
                disease_suggestions[penyakit_id]['suggested'][gid] = []
            disease_suggestions[penyakit_id]['suggested'][gid].append(rule_id)

    # Build result list
    results = []
    for pid, info in disease_suggestions.items():
        if not info['suggested']:
            continue  # All symptoms already selected for this disease

        suggested_list = []
        for gid, rule_ids in info['suggested'].items():
            suggested_list.append({
                'id_gejala': gid,
                'nama_gejala': gejala_lookup.get(gid, gid),
                'from_rules': rule_ids,
            })

        # Sort suggestions by number of rules they appear in (most relevant first)
        suggested_list.sort(key=lambda x: len(x['from_rules']), reverse=True)

        total_unique = len(info['all_symptoms'])
        matched_count = len(info['matched'])

        results.append({
            'id_penyakit': pid,
            'nama_penyakit': penyakit_lookup.get(pid, pid),
            'suggested_symptoms': suggested_list,
            'matched_count': matched_count,
            'total_needed': total_unique,
            'completion_pct': (matched_count / total_unique * 100) if total_unique > 0 else 0,
        })

    # Sort by completion percentage (most progress first), then by matched count
    results.sort(key=lambda x: (x['completion_pct'], x['matched_count']), reverse=True)

    return results


def _parse_condition(condition_str):
    """
    Parse a condition string from rules_forward.csv into a structured format.

    Supports AND and OR operators. Each condition string is either:
    - A single OR expression: "G001 OR G002 OR G003"
    - A single AND expression: "G011 AND G013 AND G015"
    - A single symptom: "G031"

    Note: Mixed AND/OR in a single rule is not expected in the data,
    but if present, AND takes precedence (evaluated first).

    Returns
    -------
    dict with keys:
        - 'type': 'AND' | 'OR' | 'SINGLE'
        - 'symptoms': list of symptom IDs
    """
    condition_str = condition_str.strip()

    if ' OR ' in condition_str:
        symptoms = [s.strip() for s in condition_str.split(' OR ')]
        return {'type': 'OR', 'symptoms': symptoms}
    elif ' AND ' in condition_str:
        symptoms = [s.strip() for s in condition_str.split(' AND ')]
        return {'type': 'AND', 'symptoms': symptoms}
    else:
        return {'type': 'SINGLE', 'symptoms': [condition_str.strip()]}


def _evaluate_condition(parsed_condition, selected_gejala_set):
    """
    Evaluate whether a parsed condition is satisfied by the selected symptoms.

    Parameters
    ----------
    parsed_condition : dict
        Output of _parse_condition()
    selected_gejala_set : set
        Set of selected symptom IDs

    Returns
    -------
    bool
        True if the condition is satisfied
    """
    symptoms = parsed_condition['symptoms']
    ctype = parsed_condition['type']

    if ctype == 'OR':
        return any(s in selected_gejala_set for s in symptoms)
    elif ctype == 'AND':
        return all(s in selected_gejala_set for s in symptoms)
    else:  # SINGLE
        return symptoms[0] in selected_gejala_set


def forward_chaining(selected_gejala, rules_fc_df, gejala_df):
    """
    Phase 1: Forward Chaining — evaluate logical rules to find triggered diseases.

    Parameters
    ----------
    selected_gejala : list
        List of selected symptom IDs
    rules_fc_df : pd.DataFrame
        Forward chaining rules with columns: id_rule, kondisi_if, id_penyakit
    gejala_df : pd.DataFrame
        Symptom dataframe for name lookups

    Returns
    -------
    dict or None
        Dictionary mapping disease ID -> list of triggered rules info, or None.
        Each triggered rule contains:
        - id_rule: rule ID
        - kondisi_if: original condition string
        - parsed: parsed condition dict
        - matched_symptoms: list of symptom IDs from this rule that the user selected
    """
    selected_set = set(selected_gejala)
    gejala_lookup = dict(zip(gejala_df['id_gejala'], gejala_df['nama_gejala']))

    triggered = {}  # id_penyakit -> [rule_info, ...]

    for _, rule in rules_fc_df.iterrows():
        rule_id = rule['id_rule']
        condition_str = rule['kondisi_if']
        penyakit_id = rule['id_penyakit']

        parsed = _parse_condition(condition_str)

        if _evaluate_condition(parsed, selected_set):
            # Find which symptoms from this rule the user actually selected
            matched_in_rule = [s for s in parsed['symptoms'] if s in selected_set]

            rule_info = {
                'id_rule': rule_id,
                'kondisi_if': condition_str,
                'parsed': parsed,
                'matched_symptoms': matched_in_rule,
            }

            if penyakit_id not in triggered:
                triggered[penyakit_id] = []
            triggered[penyakit_id].append(rule_info)

    return triggered if triggered else None


def calculate_cf(penyakit_id, selected_gejala, rules_cf_df, gejala_lookup):
    """
    Phase 2: Calculate Certainty Factor for a single disease.

    Only considers CF rules where the symptom was selected by the user.

    Parameters
    ----------
    penyakit_id : str
        Disease ID to calculate CF for
    selected_gejala : list
        Selected symptom IDs
    rules_cf_df : pd.DataFrame
        CF rules with columns: id_rule, id_penyakit, id_gejala, bobot_cf
    gejala_lookup : dict
        Mapping of symptom ID -> symptom name

    Returns
    -------
    dict
        CF calculation result with cf_akhir, persentase, matched_symptoms,
        and calculation_steps
    """
    selected_set = set(selected_gejala)

    # Get CF rules for this disease where the symptom was selected
    disease_rules = rules_cf_df[
        (rules_cf_df['id_penyakit'] == penyakit_id) &
        (rules_cf_df['id_gejala'].isin(selected_set))
    ]

    cf_old = 0
    matched_symptoms = []
    calculation_steps = []

    for _, rule_row in disease_rules.iterrows():
        cf_gejala = rule_row['bobot_cf']
        gejala_id = rule_row['id_gejala']
        gejala_nama = gejala_lookup.get(gejala_id, gejala_id)

        matched_symptoms.append({
            'id_gejala': gejala_id,
            'nama_gejala': gejala_nama,
            'bobot_cf': cf_gejala,
        })

        if cf_old == 0:
            cf_old = cf_gejala
            calculation_steps.append(
                f"CF awal = {cf_gejala} (dari gejala {gejala_id}: {gejala_nama})"
            )
        else:
            cf_new = cf_old + cf_gejala * (1 - cf_old)
            calculation_steps.append(
                f"CF_combine = {cf_old:.4f} + {cf_gejala} × (1 - {cf_old:.4f}) "
                f"= {cf_new:.4f} (gejala {gejala_id}: {gejala_nama})"
            )
            cf_old = cf_new

    return {
        'cf_akhir': cf_old,
        'persentase': cf_old * 100,
        'matched_symptoms': matched_symptoms,
        'calculation_steps': calculation_steps,
    }


def diagnose(selected_gejala, rules_cf_df, rules_fc_df, penyakit_df, gejala_df):
    """
    Full diagnosis pipeline: Forward Chaining → Certainty Factor.

    Phase 1 (Forward Chaining):
        Evaluate rules_forward.csv conditions to find which diseases
        are triggered by the selected symptoms.

    Phase 2 (Certainty Factor):
        For each triggered disease, calculate the combined CF value
        using rules_cf.csv weights.

    Parameters
    ----------
    selected_gejala : list
        List of selected symptom IDs (e.g. ['G001', 'G003'])
    rules_cf_df : pd.DataFrame
        CF rules: id_rule, id_penyakit, id_gejala, bobot_cf
    rules_fc_df : pd.DataFrame
        Forward chaining rules: id_rule, kondisi_if, id_penyakit
    penyakit_df : pd.DataFrame
        Disease data: id_penyakit, nama_penyakit
    gejala_df : pd.DataFrame
        Symptom data: id_gejala, nama_gejala

    Returns
    -------
    list[dict] or None
        Sorted list of diagnosis results (highest CF first), or None if no match.
    """
    # Phase 1: Forward Chaining
    triggered = forward_chaining(selected_gejala, rules_fc_df, gejala_df)

    if triggered is None:
        return None

    # Build lookups
    gejala_lookup = dict(zip(gejala_df['id_gejala'], gejala_df['nama_gejala']))
    penyakit_lookup = dict(zip(penyakit_df['id_penyakit'], penyakit_df['nama_penyakit']))

    hasil_diagnosa = []

    # Phase 2: Certainty Factor for each triggered disease
    for penyakit_id, fc_rules in triggered.items():
        nama_penyakit = penyakit_lookup.get(penyakit_id, penyakit_id)

        # Calculate CF
        cf_result = calculate_cf(
            penyakit_id, selected_gejala, rules_cf_df, gejala_lookup
        )

        # Build forward chaining detail for display
        fc_detail = []
        for r in fc_rules:
            # Format the condition with symptom names
            condition_readable = r['kondisi_if']
            for sid in r['parsed']['symptoms']:
                sname = gejala_lookup.get(sid, sid)
                condition_readable = condition_readable.replace(
                    sid, f"{sid} ({sname})"
                )
            fc_detail.append({
                'id_rule': r['id_rule'],
                'kondisi_if': r['kondisi_if'],
                'kondisi_readable': condition_readable,
                'matched_symptoms': r['matched_symptoms'],
            })

        hasil_diagnosa.append({
            'id_penyakit': penyakit_id,
            'nama_penyakit': nama_penyakit,
            'cf_akhir': cf_result['cf_akhir'],
            'persentase': cf_result['persentase'],
            'matched_symptoms': cf_result['matched_symptoms'],
            'calculation_steps': cf_result['calculation_steps'],
            'fc_triggered_rules': fc_detail,
        })

    # Urutkan hasil dari persentase tertinggi ke terendah
    hasil_diagnosa = sorted(
        hasil_diagnosa, key=lambda x: x['persentase'], reverse=True
    )

    return hasil_diagnosa
