import {
    keymap, highlightSpecialChars, drawSelection, highlightActiveLine, dropCursor,
    rectangularSelection, crosshairCursor,
    lineNumbers, highlightActiveLineGutter
} from "@codemirror/view"
import { Extension, EditorState } from "@codemirror/state"
import {
    defaultHighlightStyle, syntaxHighlighting, indentOnInput, bracketMatching,
    foldGutter, foldKeymap
} from "@codemirror/language"
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands"
import { searchKeymap, highlightSelectionMatches } from "@codemirror/search"
import { autocompletion, completionKeymap, closeBrackets, closeBracketsKeymap } from "@codemirror/autocomplete"
import { lintKeymap } from "@codemirror/lint"
import { json } from "@codemirror/lang-json"
import { EditorView } from '@codemirror/view';

let statusField = document.getElementById("status")!
let editor = document.getElementById("editor")!
let editorView: EditorView
let events: any[] = []

async function main(): Promise<void> {

    // @ts-ignore
    let params = (new URL(document.location)).searchParams

    let resource = params.get("profile")

    if (resource == null) {
        statusField.innerHTML = `Need the a 'profile=' query param to be present!`
        return
    }

    let serverUrl = params.get("serverUrl")

    if (serverUrl == null) {
        serverUrl = "http://localhost:5000/"
    }

    if (!serverUrl.startsWith("http")) {
        serverUrl = `https://${serverUrl}`
    }

    if (!serverUrl.endsWith("/")) {
        serverUrl = `${serverUrl}/`
    }

    let initialState = EditorState.create({
        doc: "",
        extensions: [basicSetup, json()],
    })

    editorView = new EditorView({
        parent: editor,
        state: initialState,
    })

    let textDecoder = new TextDecoder("utf-8")

    await pipeable(fetch_chunked_transfer(`${serverUrl}profile/${resource}/events`))
        .pipe(iter => mapAsyncIterable(bytes => textDecoder.decode(bytes), iter))
        .pipe(iter => mapAsyncIterable(str => str.split("\n"), iter))
        .pipe(iter => mapAsyncIterable(strs => {
            return pipeable(strs)
                .filter(isValidJson)
                .map(str => JSON.parse(str))
        }, iter))
        .pipe(flattenAsyncIterable)
        .pipe(iter => (async function* () {
            let first = true
            for await (let elem of iter) {
                if (first) {
                    first = false
                    setupStatusText(elem)
                    continue
                }
                yield elem
            }
        }()))
        .pipe(iter => mapAsyncIterable(addEvent, iter))
        .pipe(collectAsyncIterable)

}


let totalEvents = -1
function setupStatusText(ids: string[]) {
    console.log("seting up status text!")
    totalEvents = ids.length
    statusField.innerHTML = `Loaded 0 / ${totalEvents} events ...`
}

function updateStatus() {
    statusField.innerHTML = `Loaded ${events.length} / ${totalEvents} events ...`
}

function addEvent(event: any) {
    console.log("Adding event!")
    events.push(event)

    updateStatus()

    editorView.dispatch({
        changes: {
            from: 0,
            to: editorView.state.doc.length,
            insert: JSON.stringify(events, undefined, 4)
        }
    })
}


function isValidJson(s: string): boolean {
    try {
        JSON.parse(s)
        return true
    } catch (SyntaxError) {
        return false
    }
}


function pipeable<T>(v: T): T & Pipeable<T> {
    let v_ = v as T & Pipeable<T>
    v_.pipe = function <V>(f: (_: T) => V): V & Pipeable<V> {
        return pipeable(f(v_))
    }
    return v_
}


interface Pipeable<T> {
    pipe<V>(_: (_: T) => V): V & Pipeable<V>
}


async function collectAsyncIterable<T>(iter: AsyncIterable<T>): Promise<T[]> {
    let arr: T[] = []
    for await (let e of iter) {
        arr.push(e)
    }
    return arr
}


async function* logAsyncIterable<T>(iter: AsyncIterable<T>): AsyncIterable<T> {
    for await (let elem of iter) {
        console.log(elem)
        yield elem
    }
}


async function* flattenAsyncIterable<T>(iter: AsyncIterable<T[]>): AsyncIterable<T> {
    for await (let arr of iter) {
        for (let elem of arr) {
            yield elem
        }
    }
}


async function* filterAsyncIterable<T>(f: (_: T) => boolean, iter: AsyncIterable<T>): AsyncIterable<T> {
    for await (let e of iter) {
        if (f(e)) {
            yield e
        }
    }
}


async function* mapAsyncIterable<X, Y>(f: (_: X) => Y, iter: AsyncIterable<X>): AsyncIterable<Y> {
    for await (let x of iter) {
        let y = f(x)
        yield y
    }
}


async function* fetch_chunked_transfer(url: string): AsyncIterable<Uint8Array> {
    let resp = await fetch(url)
    let reader = resp.body!.getReader()
    while (true) {
        let result = await reader.read()

        if (result.done)
            return

        yield result.value
    }
}


function parseEventChunk(chunk: string): any {
    return chunk
        .split("\n")
        .filter(e => e != "")
        .map(e => { console.log(e); return e })
        .map(e => JSON.parse(e))
}


// source: https://github.com/codemirror/basic-setup/blob/main/src/codemirror.ts

// (The superfluous function calls around the list of extensions work
// around current limitations in tree-shaking software.)

/// This is an extension value that just pulls together a number of
/// extensions that you might want in a basic editor. It is meant as a
/// convenient helper to quickly set up CodeMirror without installing
/// and importing a lot of separate packages.
///
/// Specifically, it includes...
///
///  - [the default command bindings](#commands.defaultKeymap)
///  - [line numbers](#view.lineNumbers)
///  - [special character highlighting](#view.highlightSpecialChars)
///  - [the undo history](#commands.history)
///  - [a fold gutter](#language.foldGutter)
///  - [custom selection drawing](#view.drawSelection)
///  - [drop cursor](#view.dropCursor)
///  - [multiple selections](#state.EditorState^allowMultipleSelections)
///  - [reindentation on input](#language.indentOnInput)
///  - [the default highlight style](#language.defaultHighlightStyle) (as fallback)
///  - [bracket matching](#language.bracketMatching)
///  - [bracket closing](#autocomplete.closeBrackets)
///  - [autocompletion](#autocomplete.autocompletion)
///  - [rectangular selection](#view.rectangularSelection) and [crosshair cursor](#view.crosshairCursor)
///  - [active line highlighting](#view.highlightActiveLine)
///  - [active line gutter highlighting](#view.highlightActiveLineGutter)
///  - [selection match highlighting](#search.highlightSelectionMatches)
///  - [search](#search.searchKeymap)
///  - [linting](#lint.lintKeymap)
///
/// (You'll probably want to add some language package to your setup
/// too.)
///
/// This extension does not allow customization. The idea is that,
/// once you decide you want to configure your editor more precisely,
/// you take this package's source (which is just a bunch of imports
/// and an array literal), copy it into your own code, and adjust it
/// as desired.
export const basicSetup: Extension = (() => [
    lineNumbers(),
    highlightActiveLineGutter(),
    highlightSpecialChars(),
    history(),
    foldGutter(),
    drawSelection(),
    dropCursor(),
    EditorState.allowMultipleSelections.of(true),
    indentOnInput(),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
    bracketMatching(),
    closeBrackets(),
    autocompletion(),
    rectangularSelection(),
    crosshairCursor(),
    highlightActiveLine(),
    highlightSelectionMatches(),
    keymap.of([
        ...closeBracketsKeymap,
        ...defaultKeymap,
        ...searchKeymap,
        ...historyKeymap,
        ...foldKeymap,
        ...completionKeymap,
        ...lintKeymap
    ])
])()


main()
