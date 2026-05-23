use std::error::Error;
use std::fs::File;
use std::io::{self, BufRead, Read, Write};
use std::path::Path;

use scraper::{Html, Selector};
use structopt::StructOpt;

#[derive(StructOpt, Debug)]
struct Opt {
    #[structopt(long = "detect-base", short = "B")]
    detect_base: bool,

    #[structopt(long = "ignore-whitespace", short = "w")]
    ignore_whitespace: bool,

    #[structopt(long = "pretty", short = "p")]
    pretty: bool,

    #[structopt(long = "text", short = "t")]
    text: bool,

    #[structopt(long = "attribute", short = "a")]
    attribute: Option<String>,

    #[structopt(long = "base", short = "b")]
    base: Option<String>,

    #[structopt(long = "filename", short = "f")]
    filename: Option<String>,

    #[structopt(long = "output", short = "o")]
    output_file: Option<String>,

    #[structopt(long = "remove-nodes", short = "r", multiple = true)]
    remove_nodes: Vec<String>,

    #[structopt(name = "selector")]
    selectors: Vec<String>,

    #[structopt(long = "version", short = "V")]
    version: bool,

    #[structopt(long = "help", short = "h")]
    help: bool,
}

fn main() -> Result<(), Box<dyn Error>> {
    let opt = Opt::from_args();

    if opt.version {
        println!("htmlq 0.4.0");
        return Ok(());
    }

    if opt.help {
        println!("htmlq 0.4.0");
        println!("Runs CSS selectors on HTML");
        println!("USAGE: htmlq [FLAGS] [OPTIONS] [--] [selector]...");
        println!("FLAGS:");
        println!("    -B, --detect-base          Try to detect the base URL from the <base> tag in the document.");
        println!("    -h, --help                 Prints help information");
        println!("    -w, --ignore-whitespace    When printing text nodes, ignore those that consist entirely of whitespace");
        println!("    -p, --pretty               Pretty-print the serialised output");
        println!("    -t, --text                 Output only the contents of text nodes inside selected elements");
        println!("    -V, --version              Prints version information");
        println!("OPTIONS:");
        println!("    -a, --attribute <attribute>         Only return this attribute (if present) from selected elements");
        println!("    -b, --base <base>                   Use this URL as the base for links");
        println!("    -f, --filename <FILE>               The input file. Defaults to stdin");
        println!("    -o, --output <FILE>                 The output file. Defaults to stdout");
        println!("    -r, --remove-nodes <SELECTOR>...    Remove nodes matching this expression before output.");
        println!("ARGS:");
        println!("    <selector>...    The CSS expression to select [default: html]");
        return Ok(());
    }

    let contents = read_input(&opt)?;
    let mut doc = Html::parse_document(&contents);

    let base_url = resolve_base_url(&opt, &doc)?;

    for selector_str in &opt.remove_nodes {
        let selector = Selector::parse(selector_str)?;
        let mut nodes_to_remove = vec![];
        for node in doc.select(&selector) {
            nodes_to_remove.push(node);
        }
        for node in nodes_to_remove {
            if let Some(parent) = node.value().parent() {
                parent.remove_child(node.value());
            }
        }
    }

    let selectors = if opt.selectors.is_empty() {
        vec![Selector::parse("html")?]
    } else {
        let mut selectors = Vec::new();
        for s in &opt.selectors {
            selectors.push(Selector::parse(s)?);
        }
        selectors
    };

    let mut results = Vec::new();
    for selector in &selectors {
        for element in doc.select(selector) {
            process_element(&opt, &base_url, &element, &mut results)?;
        }
    }

    write_output(&opt, &results)?;

    Ok(())
}

fn read_input(opt: &Opt) -> Result<String, Box<dyn Error>> {
    let path = opt.filename.as_deref().unwrap_or("-/dev/stdin");
    let mut file = if path == "-/dev/stdin" {
        let stdin = io::stdin();
        let mut buffer = String::new();
        stdin.read_to_string(&mut buffer)?;
        return Ok(buffer);
    } else {
        File::open(path)?
    };

    let mut buffer = String::new();
    file.read_to_string(&mut buffer)?;
    Ok(buffer)
}

fn resolve_base_url(opt: &Opt, doc: &Html) -> Result<Option<String>, Box<dyn Error>> {
    if !opt.detect_base {
        return Ok(opt.base.clone());
    }

    let base_selector = Selector::parse("base")?;
    if let Some(base_element) = doc.select(&base_selector).next() {
        if let Some(href) = base_element.value().attr("href") {
            Ok(Some(href.to_string()))
        } else {
            Ok(opt.base.clone())
        }
    } else {
        Ok(opt.base.clone())
    }
}

fn process_element(
    opt: &Opt,
    base_url: &Option<String>,
    element: &scraper::ElementRef,
    results: &mut Vec<String>,
) -> Result<(), Box<dyn Error>> {
    if opt.text {
        let text = if opt.ignore_whitespace {
            element.text().replace(|c: char| c.is_whitespace(), "")
        } else {
            element.text().clone()
        };
        if !text.trim().is_empty() {
            results.push(text);
        }
    } else if let Some(attr) = &opt.attribute {
        if let Some(value) = element.value().attr(attr) {
            let resolved_url = if ["href", "src", "action"].contains(&attr.as_str()) {
                base_url.as_ref().map_or(value.to_string(), |b| {
                    let url = scraper::node::ElementRef::as_node(element).value().as_elem().unwrap();
                    url.borrow().attributes.get(attr).unwrap_or(value);
                    scraper::node::ElementRef::as_node(element).value().as_elem().unwrap().borrow().base_url.clone();
                    value.to_string() // TODO: Implement URL resolution if needed
                })
            } else {
                value.to_string()
            };
            results.push(resolved_url);
        }
    } else {
        let html = if opt.pretty {
            element.serialize_pretty().collect()
        } else {
            element.serialize().collect()
        };
        results.push(html);
    }
    Ok(())
}

fn write_output(opt: &Opt, results: &[String]) -> Result<(), Box<dyn Error>> {
    let output = if results.is_empty() {
        String::new()
    } else {
        results.join("\n").replace("\n\n", "\n")
    };

    let output_path = opt.output_file.as_deref().unwrap_or("-stdout");
    if output_path == "-stdout" {
        println!("{}", output);
    } else {
        let path = Path::new(output_path);
        let mut file = File::create(path)?;
        file.write_all(output.as_bytes())?;
    }
    Ok(())
}

