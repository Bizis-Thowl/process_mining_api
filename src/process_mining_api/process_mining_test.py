import pm4py
import pandas as pd
import csv
import io


def simple_bpmn(contents, filename):
    decoded_contents = contents.decode("utf-8")
    df = pd.read_csv(io.StringIO(decoded_contents))
    df["activity_new"] = df["activity"] + "-" + df["elementid"]
    log = pm4py.format_dataframe(df, case_id='caseid', activity_key='activity_new', timestamp_key='timestamp')
    tree = pm4py.discover_process_tree_inductive(log)
    bpmn_graph = pm4py.convert_to_bpmn(tree)
    xml = pm4py.objects.bpmn.exporter.variants.etree.get_xml_string(bpmn_graph)
    return {"filename": filename, "data": xml}
