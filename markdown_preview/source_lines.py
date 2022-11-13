# python3 -m markdown -x source_lines:SourceLinesExtension example.md

from markdown.extensions import Extension
from markdown.blockparser import BlockParser
from markdown.blockprocessors import BlockProcessor
import re
import types
import xml.etree.ElementTree as etree

def set_source_position(block, line):
   class BlockWithSourcePosition(type(block)):
      def set_source_position(self, line):
         self.source_line = line
         return self
   return BlockWithSourcePosition(block).set_source_position(line)

def parseBlocks(self, parent, _blocks):
   if not BlockParser.first_run:
      self._parseBlocks(parent, _blocks)
      return
   BlockParser.first_run = False
   source_line = 1
   blocks = []
   for b in _blocks:
      new_lines = re.search('[^\n]|$', b, re.MULTILINE).start()
      blocks.append(set_source_position(b, source_line+new_lines))
      source_line += b.count('\n')+2
   self._parseBlocks(parent, blocks)

def block_processor_run(self, parent, blocks):
   if len(parent)>0 and not parent[-1].get("source-line"):
      parent[-1].set("source-line", str(BlockParser.source_line))
      setattr(BlockParser, "source_line", None)
   try:
      setattr(BlockParser, "source_line", blocks[0].source_line)
   except Exception:
      pass
   result = self._run(parent, blocks)
   if len(parent)>0 and not parent[-1].get("source-line") and BlockParser.source_line:
      parent[-1].set("source-line", str(BlockParser.source_line))
      setattr(BlockParser, "source_line", None)
   return result

_parseBlocks = BlockParser.parseBlocks
BlockProcessor_run = BlockProcessor.run

class SourceLinesExtension(Extension):
    def extendMarkdown(self, md):
        BlockParser._parseBlocks = _parseBlocks
        BlockParser.parseBlocks = parseBlocks
        BlockParser.first_run = True
        md.parser._parseBlocks = types.MethodType(BlockParser._parseBlocks, md.parser)
        md.parser.parseBlocks = types.MethodType(parseBlocks, md.parser)
        setattr(BlockParser, "source_line", None)

        BlockProcessor._run = BlockProcessor_run
        BlockProcessor.run = block_processor_run
        for b in md.parser.blockprocessors:
           b._run = b.run
           b.run = types.MethodType(block_processor_run, b)
