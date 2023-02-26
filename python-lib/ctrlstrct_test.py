# encoding: utf-8
# ctrlstrct_test.py

"""
Test determining of errors can be made by a student
during step-by-step construction of given algorithm's execution trace.

"""

import atexit
import json
import os
from glob import glob
from pathlib import Path

import external_run
import trace_gen.styling
from ctrlstrct_run import process_algtraces
from onto_helpers import delete_ontology
from trace_gen.json2alg2tr import act_line_for_alg_element
from trace_gen.dict_helpers import get_ith_expr_value, find_by_keyval_in


def process_algorithm_and_trace_from_json(alg_tr: dict):
    """
    Demonstration entry point
    :param alg_tr: a dict with at least keys "trace", "algorithm"
    :return: feedback{"messages": [...], "mistakes": [...]}
    """
    feedback = {"messages": []}

    # validate input alg_tr
    # {
    #     "trace_name"    : str,
    #     "algorithm_name": str,
    #     "trace"         : list,
    #     "algorithm"     : dict,
    #     "header_boolean_chain" : list of bool,
    # }
    try:
        assert alg_tr, f"Empty data"
        assert type(alg_tr) == dict, f"'JSON data is not a dict!";
        key = "trace_name"
        t = str
        assert key in alg_tr, f"Key '{key}' is missing"
        assert type(alg_tr[key]) == t, f"'{key}' -> is not a {str(t)}"
        key = "algorithm_name"
        t = str
        assert key in alg_tr, f"Key '{key}' is missing"
        assert type(alg_tr[key]) == t, f"'{key}' -> is not a {str(t)}"
        key = "trace"
        t = list
        assert key in alg_tr, f"Key '{key}' is missing"
        assert type(alg_tr[key]) == t, f"'{key}' -> is not a {str(t)}"
        key = "algorithm"
        t = dict
        assert key in alg_tr, f"Key '{key}' is missing"
        assert type(alg_tr[key]) == t, f"'{key}' -> is not a {str(t)}"
    except AssertionError as e:
        feedback["messages"] += [f"JSON error: {str(e)}\n{alg_tr}"]
        return feedback

    alg_trs = [alg_tr]

    if not alg_trs:
        feedback["messages"] += ["Nothing to process: no valid algorithm / trace found."]
        return feedback

    # call it
    mistakes, err_msg = process_algorithms_and_traces(alg_trs)

    if err_msg:
        feedback["messages"] += [err_msg]
    else:
        feedback["messages"] += ["Processing of algorithm & trace finished OK."]
        feedback["mistakes"] = mistakes

    return feedback


def make_act_json(algorithm_json, algorithm_element_id: int, act_type: str, existing_trace_json,
                  user_language=None) -> list:
    """
    act_type: 'started' or 'finished' for complex, 'performed' for simple statements
    Returns full supplemented trace: list of dicts, each dict represents act object.
    (Returns string with error description if an exception occurred)
    """
    # filter out incorrect acts (if any)
    existing_trace_json = existing_trace_json or ()
    existing_trace_list = [act for act in existing_trace_json if act["is_valid"] == True]

    try:
        elem = algorithm_json["id2obj"].get(algorithm_element_id,
                                            algorithm_json["id2obj"].get(str(algorithm_element_id)))

        assert elem, f"No element with id={algorithm_element_id} in given algorithm."

        max_id = max(a['id'] for a in existing_trace_list) if existing_trace_list else 100 - 1

        result_acts = []
        # make line "program began" first
        if len(existing_trace_list) == 0 and elem['id'] != algorithm_json["entry_point"]['id']:
            # создать строку "program began"
            act_text = act_line_for_alg_element(algorithm_json, phase='started',
                                                lang=user_language, )  # передаём сам корень алгоритма, так как его type=='algorithm',
            max_id += 1
            html_tags = trace_gen.styling.prepare_tags_for_line(act_text)
            result_acts.append({
                'executes': algorithm_json["entry_point"]['id'],
                # ! а привязываем к глобальному коду (или функции main)
                'name': algorithm_json["entry_point"]['name'],
                'phase': 'started',
                'as_string': act_text,
                # 'as_tags': html_tags,
                'as_html': trace_gen.styling.to_html(html_tags),
                'id': max_id,
                'n': 1,
                'is_valid': True  # в начале трассы акт всегда такой
            })

        exec_time = 1 + len(
            [a for a in existing_trace_list if a['executes'] == algorithm_element_id and a['phase'] == act_type])

        expr_value = None
        if elem['type'] == "expr" and act_type in ('finished', 'performed'):
            name = elem['name']
            expr_list = algorithm_json['expr_values'].get(name, None)

            assert expr_list is not None, f"No expression values provided for expression '{name}' in given algorithm."

            expr_value = get_ith_expr_value(expr_list, exec_time - 1)

            # assert expr_value is not None, f"Not enough expression values provided for expression '{name}': '{expr_list}' provided, # {exec_time} requested."
            if expr_value is None:
                expr_value = False
                print(f"Info: use default value: {expr_value} for expression '{name}'.")

        act_text = act_line_for_alg_element(
            elem,
            phase=act_type,
            lang=user_language,
            expr_value=expr_value,
            use_exec_time=exec_time,
        )
        max_id += 1
        html_tags = trace_gen.styling.prepare_tags_for_line(act_text)
        act_json = {
            'executes': elem['id'],
            'name': elem['name'],
            'phase': act_type,
            'as_string': act_text,
            # 'as_tags': html_tags,
            'as_html': trace_gen.styling.to_html(html_tags),
            'id': max_id,
            'n': exec_time,
            'is_valid': None,  # пока нет информации о корректности такого акта
            # 'is_valid': True,  # debug !!
        }
        if expr_value is not None:
            act_json['value'] = expr_value

        result_acts.append(act_json)

        return existing_trace_list + result_acts
    except Exception as e:
        # raise e
        return f"Server error in make_act_json() - {type(e).__name__}:\n\t{str(e)}"


def add_styling_to_trace(algorithm_json, trace_json, user_language=None, comment_style=None, add_tags=False) -> list:
    """Adds text line, tags and html form for each act in given trace and returns the same reference to the trace list
    comment_style: {None | 'use' | 'highlight'}
    """
    try:
        assert isinstance(trace_json, (list, tuple)), "The trace was not correctly constructed: " + str(trace_json)

        for act_dict in trace_json:

            algorithm_element_id = act_dict['executes']
            elem = algorithm_json["id2obj"].get(algorithm_element_id,
                                                algorithm_json["id2obj"].get(str(algorithm_element_id), None))

            assert elem, f"No element with id={algorithm_element_id} in given algorithm."

            if elem['id'] == algorithm_json["entry_point"]['id']:
                # создать строку типа "program began"
                # act_text = act_line_for_alg_element(algorithm_json, phase='started', lang=user_language, )  # передаём сам корень
                elem = algorithm_json

            act_text = act_line_for_alg_element(
                elem,
                phase=act_dict['phase'],
                lang=user_language,
                expr_value=act_dict.get('value', None),
                use_exec_time=int(act_dict['n']),
            )
            if 'comment' in act_dict and act_dict['comment'] and comment_style is not None:
                act_text += "    // " + act_dict['comment']

            html_tags = trace_gen.styling.prepare_tags_for_line(act_text)

            if 'comment' in act_dict and act_dict['comment'] and comment_style == 'highlight':
                html_tags = {
                    "tag": "span",
                    "attributes": {"class": ["warning"]},
                    "content": html_tags
                }

            add_json = {
                'as_string': act_text,
                'as_html': trace_gen.styling.to_html(html_tags),
            }
            act_dict.update(add_json)
            if add_tags:
                add_json = {
                    'as_tags': html_tags,
                }
                act_dict.update(add_json)

        return trace_json
    except Exception as e:
        # raise e
        return f"Server error in add_styling_to_trace() - {type(e).__name__}:\n\t{str(e)}"


def process_algorithms_and_traces(alg_trs_list: list, write_mistakes_to_acts=False) -> (
        'mistakes: list[str]', 'error_message: str or None'):
    try:
        onto, mistakes = process_algtraces(alg_trs_list, verbose=0, mistakes_as_objects=False)

        if not mistakes and len(alg_trs_list) == 1:
            # try to find automatically polyfilled acts & insert them into the trace
            # apply the simplest behaviour: skipped acts will be inserted to the previous-to-the-last position.
            if implicit_acts := list(onto.implicit_act.instances()):
                implicit_acts.sort(key=lambda a: a.id)
                acts_count = len(implicit_acts)
                print(acts_count, 'implicit_acts found, inserting them into trace.')

                algorithm = alg_trs_list[0]["algorithm"]
                # to be modified in-place (new acts will be inserted to prev. to the last)
                mutable_trace = alg_trs_list[0]["trace"]

                for imp_act in implicit_acts:
                    bound = imp_act.executes
                    assert bound
                    st = bound.boundary_of
                    assert st
                    algorithm_element_id = st.id
                    if onto.act_end in imp_act.is_a:
                        act_type = "finished"
                    elif onto.act_begin in imp_act.is_a:
                        act_type = "started"
                    else:
                        raise ValueError("implicit act has no begin/end type!: %s" % imp_act)
                    appended_trace = make_act_json(algorithm_json=algorithm, algorithm_element_id=algorithm_element_id,
                                                  act_type=act_type, existing_trace_json=mutable_trace[:-1],
                                                  user_language=None)
                    assert len(appended_trace) >= 2, appended_trace
                    mutable_trace.insert(-1, appended_trace[-1])
            # end for

            if finish_trace_acts := list(onto.finish_trace_act.instances()):
                # finish_trace_act exists => finish the trace.

                print('finish_trace_act found, closing the trace.')
                act = finish_trace_acts[0]

                algorithm = alg_trs_list[0]["algorithm"]
                # to be modified in-place (new acts will be inserted to prev. to the last)
                mutable_trace = alg_trs_list[0]["trace"]

                bound = act.executes
                assert bound
                end_of_trace_bound = bound.consequent[0]
                assert end_of_trace_bound
                st = end_of_trace_bound.boundary_of
                assert st

                algorithm_element_id = st.id
                act_type = "finished"

                appended_trace = make_act_json(algorithm_json=algorithm, algorithm_element_id=algorithm_element_id,
                                              act_type=act_type, existing_trace_json=mutable_trace[:],
                                              user_language=None)

                assert len(appended_trace) >= 2, appended_trace
                new_last_line = appended_trace[-1]

                # создать строку "program ended"
                act_text = act_line_for_alg_element(algorithm, phase='finished',
                                                    lang=None, )  # передаём сам корень алгоритма, так как его type=='algorithm',
                # обновить в строке трассы, т.к. по умолчанию генерируется 'следование global_code закончилось 1-й раз'
                new_last_line["as_string"] = act_text
                html_tags = trace_gen.styling.prepare_tags_for_line(act_text)
                new_last_line['as_html'] = trace_gen.styling.to_html(html_tags)

                mutable_trace.append(new_last_line)
                ### print("+=+ inserted closing act:", new_last_line["as_string"])

        delete_ontology(onto)

        if write_mistakes_to_acts and len(alg_trs_list) != 1:
            print("** Warning!: write_mistakes_to_acts is inapplicable when traces count =", len(alg_trs_list), "(!=1)")
        if write_mistakes_to_acts and len(alg_trs_list) == 1:
            # ошибки нужны, и сейчас не режим тестирования
            trace = alg_trs_list[0]['trace']
            for mistake in mistakes:
                act_id = mistake["id"][0]
                for act_obj in list(find_by_keyval_in("id", act_id, trace)):
                    new_explanations = act_obj.get("explanations", []) + mistake["explanations"]
                    act_obj["explanations"] = sorted(set(new_explanations))
                    if not act_obj["explanations"]:  # был пустой список - запишем хоть что-то
                        act_obj["explanations"] = ["Ошибка обнаружена, но вид ошибки не определён."]
                    act_obj["mistakes"] = mistake
                    act_obj["is_valid"] = False
                    if 'value' in act_obj:
                        print(" ***** Reset expr evaluation value.")
                        act_obj["value"] = "not evaluated"
                        # del act_obj["value"]
                        alg_data = alg_trs_list[0]['algorithm']
                        # rewrite this act
                        add_styling_to_trace(alg_data, [act_obj])
                # break

            # Apply correctness mark to other acts:  act_obj["is_valid"] = True
            for act_obj in trace:
                if act_obj["is_valid"] is None:
                    act_obj["is_valid"] = True

            # Признак окончания трассы
            # set act_obj["is_final"] = True for end of the topmost statement
            top_stmts = set()
            for alg_obj in find_by_keyval_in("type", "algorithm", alg_trs_list):
                top_stmts.add(alg_obj["entry_point"]["body"][-1]["id"])
            assert top_stmts, top_stmts

            for act_obj in trace:
                if (act_obj["is_valid"] == True
                        and act_obj["phase"] in ('finished', "performed")
                        and act_obj["executes"] in top_stmts):
                    act_obj["is_final"] = True

        return mistakes, None
    except Exception as e:
        msg = "Exception occured in process_algorithms_and_traces(): %s: %s" % (str(type(e)), str(e))
        raise e
        print(msg)
        return [], msg


def run_tests(input_directory="../data/python/", output_directory="../results/"):
    test_results = {}
    try:
        for file in glob(os.path.join(input_directory, '*.json')):
            path = Path(file)
            print("processing test:", path.name)
            with open(path) as f:
                input_data = json.load(f)

            results = process_algorithm_and_trace_from_json(input_data)

            test_results[path.stem] = results

    except Exception as e:
        print()
        print("processing tests interrupted with the following exception:")
        msg = "Exception occurred in run_tests(): %s: %s" % (str(type(e)), str(e))
        print(msg)
        raise e

    finally:
        with open(Path(output_directory, "python_results.json"), 'w') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

    print("processing tests finished.")


if __name__ == '__main__':
    # try to close the external process if it will still be running on Python program end
    atexit.register(external_run.stop_jena_reasoning_service)

    run_tests()

    # close the external process
    external_run.stop_jena_reasoning_service()
    atexit.unregister(external_run.stop_jena_reasoning_service)
