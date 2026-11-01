import io
import tarfile

from pipeline.chembl import extract, read

DUMP = """CREATE TABLE `activities` (
  `activity_id` bigint(20) NOT NULL,
  `assay_id` bigint(20) NOT NULL,
  `doc_id` bigint(20) DEFAULT NULL,
  `record_id` bigint(20) NOT NULL,
  `molregno` bigint(20) DEFAULT NULL,
  `standard_type` varchar(250) DEFAULT NULL,
  `activity_comment` varchar(4000) DEFAULT NULL,
  `data_validity_comment` varchar(30) DEFAULT NULL,
  `potential_duplicate` tinyint(4) DEFAULT NULL,
  `pchembl_value` decimal(4,2) DEFAULT NULL,
  PRIMARY KEY (`activity_id`)
);
INSERT INTO `activities` VALUES (1,10,100,7,1000,'IC50','it\\'s, (odd)',NULL,0,7.40),(2,10,100,8,1000,'Inhibition',NULL,NULL,0,NULL);
CREATE TABLE `docs` (
  `doc_id` bigint(20) NOT NULL,
  `journal` varchar(50) DEFAULT NULL,
  `year` smallint(6) DEFAULT NULL,
  `chembl_id` varchar(20) NOT NULL,
  `src_id` int(11) DEFAULT NULL
);
INSERT INTO `docs` VALUES (100,'J. Med. Chem.',2003,'CHEMBL1144977',1),(101,NULL,NULL,'CHEMBL2',38);
CREATE TABLE `version` (
  `name` varchar(50) NOT NULL
);
INSERT INTO `version` VALUES ('ChEMBL_37');
"""


def test_the_dump_of_many_rows_per_insert_becomes_one_file_per_table_with_the_columns_used(tmp_path):
    dump = tmp_path / "chembl_mysql.tar.gz"
    data = DUMP.encode()
    with tarfile.open(dump, "w:gz") as tar:
        info = tarfile.TarInfo("chembl/chembl_mysql.dmp")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    out = str(tmp_path / "extract")
    extract(str(dump), out)

    acts = read(out, "activities")  # the activity without a pChEMBL value is left out
    assert acts.fillna("").to_dict("records") == [{"activity_id": "1", "assay_id": "10", "doc_id": "100",
                                                   "molregno": "1000", "standard_type": "IC50", "pchembl_value": "7.40",
                                                   "data_validity_comment": "", "potential_duplicate": "0"}]
    docs = read(out, "docs")
    assert list(docs.columns) == ["doc_id", "chembl_id", "year", "journal", "src_id"]
    assert docs.year.tolist()[0] == "2003" and docs.year.isna().tolist() == [False, True]
    assert not (tmp_path / "extract" / "version.tsv").exists()
