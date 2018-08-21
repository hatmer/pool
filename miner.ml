open Cohttp
open Async

(* Make request and return response or status code *)
let fetch (url_str : string) (name_str : string) =
  let url = Uri.of_string url_str in
  let headers = Cohttp.Header.prepend_user_agent (Cohttp.Header.of_list [ "connection", "close"]) name_str in
  let meth = Code.method_of_string "GET" in
    try_with (fun () -> Cohttp_async.Client.call meth ~headers url
    >>= fun (res, body) -> 
    let http_code = Cohttp.Response.status res in 
    match http_code with
    | `OK -> Cohttp_async.Body.to_string body
    | _ -> return "400" (* bad url *)
  ) >>| function    
      | Ok s -> s
      | Error _ -> "500" (* request failed *)
;; 

