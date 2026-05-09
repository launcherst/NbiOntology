# -*- coding: utf-8 -*-
# @author: daiwei.tan
# @datetime: 2026/04/26 21:03 UTC+8
# @version: 0.0.2

from pathlib import Path

from agents.data_loader import DataLoaderAgent, InstanceDataLoader, PerformanceDataLoader
from agents.ontology_generator import OntologyGenerator
from agents.instances_generator import generate_instances


EXCEL_RESOURCE = "data/NbiExampleOtnResources.xlsx"
EXCEL_PERFORMANCE = "data/NbiExampleOtnPerformance.xlsx"
DATA_DIR = "data"
OUTPUT_DIR = "output"
SAMPLE_NE = 20  # 采样 NE 数量 (控制图谱规模, None=全部)


def step1_convert_xml_to_csv():
    """步骤1: 将 NBI XML 数据转为 CSV"""
    print("=" * 50)
    print("Step 1: Converting NBI XML to CSV...")
    from agents.xml_to_csv_batch import batch_convert_xml_in_directory
    batch_convert_xml_in_directory(DATA_DIR, recursive=False)
    print()


def step2_generate_ontology():
    """步骤2: 生成本体 (TBox)"""
    print("=" * 50)
    print("Step 2: Generating Ontology...")
    loader = DataLoaderAgent(EXCEL_RESOURCE)
    standard_data = loader.load_all()

    generator = OntologyGenerator(standard_data)
    generator.generate_ontology()
    generator.print_ontology_summary()
    generator.to_rdf_lib("output/otn_ontology_lib.rdf")
    generator.to_json("output/otn_ontology_test.json")
    print()
    return generator.ontology


def step3_generate_instances():
    """步骤3: 生成实例 (ABox)"""
    print("=" * 50)
    print("Step 3: Generating Instances...")

    # 3a. Load instance data from CSV (sample by NE)
    print("  [3a] Loading instance data from CSV...")
    inst_loader = InstanceDataLoader(data_dir=DATA_DIR)
    instance_data = inst_loader.load_all(sample_ne=SAMPLE_NE)

    # 3b. Load performance definitions & generate sample records
    print("  [3b] Loading performance definitions...")
    perf_loader = PerformanceDataLoader(EXCEL_PERFORMANCE)
    perf_loader.load_definitions()
    perf_records = perf_loader.generate_sample_records(instance_data, records_per_resource=2)

    # 3c. Generate RDF instances
    print("  [3c] Generating RDF instances...")
    g = generate_instances(
        instance_data=instance_data,
        performance_records=perf_records,
        output_ttl="output/instances.ttl",
    )
    print()
    return g


def main():
    """主流水线: 本体生成 → 实例生成 → (可选)启动 Web"""
    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    # Step 1: Convert XML to CSV (skip if CSVs already exist)
    csv_files = list(Path(DATA_DIR).glob("CM-OTN-*.csv"))
    if not csv_files:
        step1_convert_xml_to_csv()
    else:
        print(f"  Found {len(csv_files)} existing CSV files, skipping XML conversion.\n")

    # Step 2: Generate Ontology
    step2_generate_ontology()

    # Step 3: Generate Instances
    step3_generate_instances()

    print("=" * 50)
    print("Pipeline complete!")
    print(f"  Ontology: output/otn_ontology_lib.rdf")
    print(f"  Instances: output/instances.ttl")
    print()
    print("To start the web interface, run:")
    print("  streamlit run app.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
