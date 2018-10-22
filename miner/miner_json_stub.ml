open Async;;
open Yojson.Basic.Util;;

(* Make request and return response or status code *)

let request (url_str : string) (verb : string) (body : string) =
  let url = Uri.of_string url_str in
  let headers = Cohttp.Header.prepend_user_agent (Cohttp.Header.of_list [] (*[ "connection", "close"]*)) "worker" in
  let meth = Cohttp.Code.method_of_string verb in
    try_with (fun () -> Cohttp_async.Client.call meth ~headers (*~body:Cohttp_async.Body.(of_string body)*) url
    >>= fun (res, body) ->
    let http_code = Cohttp.Response.status res in
    match http_code with
    | `OK -> Cohttp_async.Body.to_string body
    | _ -> return "400" (* bad url *)
  ) >>| function
      | Ok s -> s
      | Error _ -> "500" (* request failed *)
;;


(* Double SHA-256 *)

let dHash data =
    data |> Sha256.string |> Sha256.to_bin |> Sha256.string |> Sha256.to_bin
;;


(* Format converters *)

let hex_to_bin hexString =
    Hex.to_string (`Hex hexString)
;;

let bin_to_hex binString =
    Hex.of_string binString
;;
      

(* Calculate Merkle Root *)

let rec calculateMerkleRow txns = 
    match txns with
    | [] -> []
    | a::b::lst -> dHash (String.concat ~sep:"" [a; b]) :: calculateMerkleRow lst
    | a::[] -> [dHash(String.concat ~sep:"" [a; a])]
;;

let rec calculateMerkleRoot txns = 
    match txns with
    | a::[] -> a
    | a::b::lst -> calculateMerkleRoot (calculateMerkleRow txns)
    | [] -> ""
;;

type header = {
    version : int;
    hashPrevBlock : string;
    hashMerkleRoot: string;
    currentTime : int;
    bits : int;
    nonce : int;
}


let header_of_json j = {
    version = j |> member "version" |> to_int;
    hashPrevBlock = j |> member "previousblockhash" |> to_string;
    hashMerkleRoot = calculateMerkleRoot ((j |> member "coinbasetxn" 
                                             |> member "data" |> to_string) :: []);
    currentTime = j |> member "curtime" |> to_int;
    bits = j |> member "bits" |> to_int;
    nonce = 0;
}




(* Increment coinbase txn nonce *)

(*
    # construct block header using values from template

    version = 2 # block version number
    hashPrevBlock = "" # 256 bits
    hashMerkleRoot = "" # 256 bits
    time = int(time())
    #bits = # target in compact format
    nonce = 0
*)

(* hash, update nonce, repeat *)
(* keep track of best hash found for ppow *)


(* share submit format:*)
let share = "000003c48a294584f90e58325c60ca82896d071826b45680a661cec4d42";;
let share_msg = String.concat "" [{|{"id": 0, "method": "submitblock", "params": ["|};share; {|"]}|}];;

let url = "https://127.0.0.1:8000/submit?val=hi";;
let initial_request = "{'id': 0, 'method': 'getblocktemplate', 'params': [{'capabilities': ['coinbasetxn', 'workid', 'coinbase/append']}]}";;

(*request "https://127.0.0.1:8000/submit" "POST" share_msg;;*)
(*request "https://127.0.0.1:8000/fetch" "GET" "hi";;*)
request "https://127.0.0.1:8000/fetch" "GET" initial_request;;

let () = 

    request "https://127.0.0.1:8000/fetch" "GET" initial_request
    >>| Yojson.Basic.from_string >>| member "result" >>|
    try header_of_json
    with Type_error (s, _) -> failwith ("Received bad json from server: " ^ s);
    
    don't_wait_for (exit 0);
    Core.never_returns (Scheduler.go ())
;;
