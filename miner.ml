open Cohttp
open Async

let url = "https://127.0.0.1:8000/fetch"
let badurl = "https://127.0.0.1:8000/fe"
let failurl = "hi"

let fetch (url_str : string) (name_str : string) =
  let url = Uri.of_string url_str in
  let headers = Cohttp.Header.prepend_user_agent (Cohttp.Header.of_list [ "connection", "close"]) name_str in
  let meth = Code.method_of_string "GET" in
    Cohttp_async.Client.call meth ~headers url
    >>= fun (res, body) -> 
    let http_code = Cohttp.Response.status res in 
    match http_code with
    | `OK -> Cohttp_async.Body.to_string body
    | _ -> return ""    
;;

let r = 
    try fetch failurl "worker"
    with _ -> return ""
;;
