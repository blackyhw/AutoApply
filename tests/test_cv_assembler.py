from autoapply.errors import UnknownCvBlockError
from autoapply.generator.blocks import BlockCatalog, CvBlock
from autoapply.generator.cv_assembler import CvAssembler


def test_assembler_only_uses_known_blocks_and_keeps_verbatim_text(catalog: BlockCatalog):
    assembler = CvAssembler(catalog)
    cv = assembler.assemble(["summary_backend", "this-block-does-not-exist"])
    assert "Desarrollador backend" in cv
    assert "this-block-does-not-exist" not in cv
    assert "Nombre Apellido" in cv
    assert "Python, FastAPI" in cv


def test_assembler_does_not_rewrite_block_content(catalog: BlockCatalog):
    original = catalog.get("exp_api_platform").content.strip()
    assembled = CvAssembler(catalog).assemble(["exp_api_platform"])
    assert original in assembled


def test_empty_selection_without_always_include_raises():
    catalog = BlockCatalog(
        [CvBlock(id="only", section="summary", content="hola", always_include=False)]
    )
    try:
        CvAssembler(catalog).assemble([])
        raise AssertionError("expected UnknownCvBlockError")
    except UnknownCvBlockError:
        pass
