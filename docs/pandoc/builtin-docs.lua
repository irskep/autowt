local function stringify(inlines)
  return pandoc.utils.stringify(inlines)
end

local function trim(value)
  return value:gsub("^%s+", ""):gsub("%s+$", "")
end

local function is_skip_start(block)
  return block.t == "RawBlock"
    and block.format == "html"
    and block.text:match("builtin%-docs:skip%-start") ~= nil
end

local function is_skip_end(block)
  return block.t == "RawBlock"
    and block.format == "html"
    and block.text:match("builtin%-docs:skip%-end") ~= nil
end

local function is_web_only_raw_block(block)
  if block.t ~= "RawBlock" or block.format ~= "html" then
    return false
  end
  if is_skip_start(block) or is_skip_end(block) then
    return false
  end
  local text = trim(block.text)
  return text:match("^<div%s") ~= nil or text == "</div>" or text:match("^<!%-%-.*%-%->$") ~= nil
end

local function parse_admonition_marker(block)
  if block.t ~= "Para" then
    return nil
  end

  local text = stringify(block.content)
  local rest = nil
  if text:sub(1, 3) == "!!!" then
    rest = text:sub(4)
  elseif text:sub(1, 3) == "???" then
    rest = text:sub(4)
    if rest:sub(1, 1) == "+" then
      rest = rest:sub(2)
    end
  else
    return nil
  end

  local kind, title = rest:match("^%s*([%w_-]+)%s*(.*)$")
  if kind == nil then
    return nil
  end

  title = trim(title or "")
  title = title:gsub('^"(.*)"$', "%1")
  title = title:gsub("^'(.*)'$", "%1")
  title = title:gsub("^“(.*)”$", "%1")
  title = title:gsub("^‘(.*)’$", "%1")
  return {
    kind = kind,
    title = title,
  }
end

local function parse_admonition_body(block)
  if block == nil or block.t ~= "CodeBlock" then
    return nil
  end
  return pandoc.read(block.text, "markdown+fenced_code_attributes").blocks
end

local function strip_material_icons(text)
  return text
    :gsub(":lucide%-[%w_-]+:%s*", "")
    :gsub("%s+:lucide%-[%w_-]+:", "")
end

function Str(el)
  local text = strip_material_icons(el.text)
  if text == "" then
    return {}
  end
  return pandoc.Str(text)
end

function CodeBlock(el)
  local title = el.attributes.title
  if title == nil or title == "" then
    return el
  end

  el.attributes.title = nil
  return {
    pandoc.Para({ pandoc.Str("File: " .. title) }),
    el,
  }
end

function RawBlock(el)
  if is_web_only_raw_block(el) then
    return {}
  end
  return el
end

function HorizontalRule()
  return {}
end

function Pandoc(doc)
  local result = pandoc.List()
  local skipping = false
  local i = 1

  while i <= #doc.blocks do
    local block = doc.blocks[i]

    if skipping then
      if is_skip_end(block) then
        skipping = false
      end
      i = i + 1
    elseif is_skip_start(block) then
      skipping = true
      i = i + 1
    else
      local marker = parse_admonition_marker(block)
      if marker ~= nil then
        local body = parse_admonition_body(doc.blocks[i + 1])
        if body ~= nil then
          local label = string.upper(marker.kind:sub(1, 1)) .. marker.kind:sub(2) .. ":"
          if marker.title ~= "" then
            label = label .. " " .. marker.title
          end
          result:insert(pandoc.Para({ pandoc.Str(label) }))
          for _, body_block in ipairs(body) do
            result:insert(body_block)
          end
          i = i + 2
        else
          result:insert(block)
          i = i + 1
        end
      else
        result:insert(block)
        i = i + 1
      end
    end
  end

  doc.blocks = result
  return doc
end
