

let url = "127.0.0.1:8000/fetch"

let fetch (uri : string) =
  let meth = Cohttp.Code.method_of_string "GET" in
  let uri = Uri.of_string uri in
  let headers = 
    Cohttp.Header.prepend_user_agent (Cohttp.Header.of_list [ "connection", "close" ]) "worker" in
  
  Cohttp_async.Client.call meth ~headers ~body:Cohttp_async.Body.(of_string "") uri
  >>| fun (res, body) ->
  let http_code = Cohttp.Response.status res in 
  match http_code with
  | `OK -> Cohttp_async.Body.to_string body
  | _ -> "None"
;;

fetch url;;
