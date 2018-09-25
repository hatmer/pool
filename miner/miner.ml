open Async;;

(* Make request and return response or status code *)
let fetch (url_str : string) (name_str : string) =
  let url = Uri.of_string url_str in
  let headers = Cohttp.Header.prepend_user_agent (Cohttp.Header.of_list [ "connection", "close"]) name_str in
  let meth = Cohttp.Code.method_of_string "GET" in
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


(* Double SHA-256 of data received from server *)
let hash block =
    block |> Sha256.string |> Sha256.to_bin |> Sha256.string |> Sha256.to_hex
;;

(* keep track of best hash found for ppow *)

let url = "https://127.0.0.1:8000/submit?val=hi";;


let () = 
    print_endline (hash "hello");
    don't_wait_for (exit 0);
    Core.never_returns (Scheduler.go ())
;;
