from pipeline.unii import parents

TAK418 = "N(CC1CC1)[C@H]2[C@@H](C2)c3cc(cs3)C(NC4CCOCC4)=O"


def record(unii, smiles, kind="INGREDIENT SUBSTANCE"):
    return {"UNII": unii, "SMILES": smiles, "INGREDIENT_TYPE": kind}


def test_a_salt_or_hydrate_points_to_the_record_of_its_neutral_component_however_the_smiles_is_written():
    records = [
        record("TAK418HCL", f"{TAK418}.Cl"),
        record("TAK418BASE", TAK418),
        record("PICOSULFATE_NA_H2O", "c1ccnc(c1)C(c2ccc(cc2)OS(=O)(=O)[O-])c3ccc(cc3)OS(=O)(=O)[O-].[Na+].O.[Na+]"),
        record("PICOSULFURIC_ACID", "c1ccnc(c1)C(c2ccc(cc2)OS(=O)(=O)O)c3ccc(cc3)OS(=O)(=O)O"),
        record("IMATINIB_MESYLATE", "S(=O)(=O)(O)C.c1(nc(-c2cnccc2)ccn1)Nc3cc(NC(c4ccc(CN5CCN(CC5)C)cc4)=O)ccc3C"),
        record("IMATINIB", "Cc1ccc(cc1Nc2nccc(-c3cccnc3)n2)NC(=O)c4ccc(cc4)CN5CCN(C)CC5"),
        record("SODIUM_CHLORIDE", "[Na+].[Cl-]"),
        record("TADNERSEN_SODIUM", ""),
    ]
    assert parents(records) == {("TAK418HCL", "TAK418BASE"), ("PICOSULFATE_NA_H2O", "PICOSULFURIC_ACID"),
                                ("IMATINIB_MESYLATE", "IMATINIB")}


def test_a_counter_ion_found_in_many_salts_is_no_parent():
    acid = "CS(=O)(=O)O"
    records = [record("MESYLIC_ACID", acid)]
    records += [record(f"SALT{i}", f"{acid}.{'C' * (i + 2)}N") for i in range(51)]
    assert parents(records) == set()
