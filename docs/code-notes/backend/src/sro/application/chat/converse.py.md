# Notes for `backend/src/sro/application/chat/converse.py`

Comments and docstrings moved out of [`backend/src/sro/application/chat/converse.py`](../../../../../../../backend/src/sro/application/chat/converse.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/chat/converse.py#L1): Docstring

> Say something to the system, and get back what it worked out.
>
> The reply is never improvised. It is a rendering of a `Resolution`: the skill
> that was matched and what it still needs, the choice between two that were too
> close, or what the knowledge base knows about a task nobody has taught. The
> prose exists so an operator can read it; the decision is stored beside it so an
> auditor does not have to.
>
> **Nothing is performed here.** A matched skill is offered, and starting it is a
> separate request the operator makes — which is what makes their confirmation
> the authorisation an assisted run records.

## module, [line 1120](../../../../../../../backend/src/sro/application/chat/converse.py#L1120): Note on the line above

Code: `LOOKED = "looked"`

> The decision a lookup's answer rides on into the conversation.
>
> Its own kind, and not `note`: the panel draws it with `result()`, which counts
> the records and puts the first few in a table. A kind nobody recognises is a
> sentence, and a sentence about fifty records is the raw-JSON preview this
> replaced.

## module, [line 1123](../../../../../../../backend/src/sro/application/chat/converse.py#L1123): Note on the line above

Code: `K_RAN_OUT = ("timeout", "timed out", "deadline")`

> What the channel says when nobody answered in time. The extension's own
> words, matched here rather than translated -- `unreachable` is a browser that
> said no and this is one that said nothing, and they want different sentences.

## `_NotAsked`, [line 77](../../../../../../../backend/src/sro/application/chat/converse.py#L77): Docstring

> Nobody has placed this sentence against the jobs yet.
>
> A sentinel rather than `None`, because `None` is already an answer on this
> path -- it is what `_placed_by_the_rig` returns for a sentence that names
> no job, which is exactly the case that must not be confused with "not
> looked at".

## `_why_it_failed`, [line 974](../../../../../../../backend/src/sro/application/chat/converse.py#L974): Docstring

> Say what actually went wrong, in the words of the thing that went wrong.
>
> "1 step did not satisfy their post-conditions" is true of a skill that has
> drifted, a system that is down, and a session that has expired, and those
> want three different people to do three different things. The step already
> knows which; it was just not being read.

## `_what_happened`, [line 988](../../../../../../../backend/src/sro/application/chat/converse.py#L988): Docstring

> One line about a run, in the words of what it did.

## `_reply`, [line 1004](../../../../../../../backend/src/sro/application/chat/converse.py#L1004): Docstring

> What to say. Every branch says what happens next, because a reply that
> only reports a state leaves the operator to guess at the next move.

## `_last_time`, [line 1038](../../../../../../../backend/src/sro/application/chat/converse.py#L1038): Docstring

> What the demonstrations used, where that is all anybody has to go on.
>
> A parameter that exists because an operator asked to be prompted for it was
> a constant a moment ago, and saying what it was is the difference between a
> question somebody can answer and one they have to go and look up.

## `_what_it_found`, [line 1049](../../../../../../../backend/src/sro/application/chat/converse.py#L1049): Docstring

> What a composed read found, in the words of the question.

## `_derived`, [line 1061](../../../../../../../backend/src/sro/application/chat/converse.py#L1061): Docstring

> A composed read, as the console renders any other answer.
>
> Carried with where it came from: a request this system wrote is only
> trustworthy if the operator can see what it was built out of.

## `_decision`, [line 1077](../../../../../../../backend/src/sro/application/chat/converse.py#L1077): Docstring

> The structured half of the reply, kept for the audit trail.

## `_last_asked`, [line 1101](../../../../../../../backend/src/sro/application/chat/converse.py#L1101): Docstring

> The operator's previous sentence, which is where a follow-up's subject is.
>
> Theirs rather than the assistant's: the reply is full of words the system
> chose, and letting those steer the next match would have the console
> talking to itself.

## `_awaiting`, [line 1108](../../../../../../../backend/src/sro/application/chat/converse.py#L1108): Docstring

> The skill the last reply asked for values for, if it is still waiting.

## `_seen`, [line 1131](../../../../../../../backend/src/sro/application/chat/converse.py#L1131): Docstring

> One answer, in the shape every surface draws it from. See
> `application.lookup.answer.as_seen` -- the trimming is there so the card, the
> conversation and a model asked to read it all get the same answer.

## `_what_was_found`, [line 1143](../../../../../../../backend/src/sro/application/chat/converse.py#L1143): Docstring

> The sentence above the table, for a surface that draws no table.
>
> Deliberately thin. What the answer SAYS is in the records, and a sentence
> claiming to summarise them would be this system inventing a number: the
> table is the answer and this is its label.

## `_nothing_back`, [line 1161](../../../../../../../backend/src/sro/application/chat/converse.py#L1161): Docstring

> "Nothing back from them yet" -- where a mail is what is being waited on.
>
> Read off the thread rather than guessed: the last mail this conversation
> sent, and the fact that its answer has not arrived. The second half needs
> no checking. A reply that had been read would have filled the value, and
> this sentence is only ever written while the question is still standing.
>
> Empty for a question nobody was mailed about, which is most of them: a run
> that came up short in front of a person asks the person.

## `_the_way_out`, [line 1173](../../../../../../../backend/src/sro/application/chat/converse.py#L1173): Docstring

> How to be taken at your word, said where it is needed.
>
> Every re-ask happens because a reading refused to take a sentence as the
> value, and that reading is told to refuse when it is unsure -- which is
> the right default and leaves somebody who typed a real value with no move
> except typing it again and being refused again. `question` already names
> that loop as the thing this design must not be, for the length case. This
> is the same exit for the reading case: `said_as_the_value` takes a value
> the person named themselves without asking anybody, and this is the only
> place they are ever told so.

## `_gathered`, [line 1178](../../../../../../../backend/src/sro/application/chat/converse.py#L1178): Docstring

> Every value established so far **for this skill**.
>
> Read back off the decisions rather than held in memory: the thread is what
> survives a restart, and an operator answering three questions over five
> minutes should not depend on a process staying up.
>
> Filtered by skill, which the docstring always claimed and the code never
> did: it merged the values from every decision in the thread, so a thread
> where somebody asked about suppliers and then went on to create a client
> carried the supplier's values into the client's parameters. Values arriving
> from somewhere the operator never typed them is the worst possible way for a
> write to be wrong -- it looks answered.
>
> Nothing is gathered when nothing is being waited on. A fresh sentence brings
> its own values; the thread's older ones belong to whatever they were for.

## `Converse.note`, [line 116](../../../../../../../backend/src/sro/application/chat/converse.py#L116): Docstring

> Write something into the thread that nobody asked a question for.
>
> A pursuit finishes minutes after the request that started it, in a
> background task, and its progress lives only in this process. What it
> did has to end up somewhere an operator can read tomorrow.

## `Converse._carry_on`, [line 215](../../../../../../../backend/src/sro/application/chat/converse.py#L215): Docstring

> Everything this door does with a sentence that answers no question.
>
> The body of `execute` from the question check down, unchanged and
> named, so that a sentence which turned out NOT to be an answer can be
> handled the ordinary way rather than being dropped for not fitting a
> box it was never about.

## `Converse._still_wanted`, [line 310](../../../../../../../backend/src/sro/application/chat/converse.py#L310): Docstring

> The standing question, minus anything the job no longer asks for.
>
> A question stands until it is answered or the job is dropped, and that
> is right -- it is what stops an ordinary reply burying it. What it
> missed is that the JOB can change underneath it. A field the job
> demanded on Monday may be one the page never asked for, learnt as a
> parameter only because two demonstrations happened to vary it, and
> since 2026-09-22 no longer demanded at all.
>
> Measured on the deployment that day. `Department takes 10 characters.
> What should it be?` was asked at 11:35 and was still being re-asked at
> 13:50 -- two hours and four unrelated sentences later, under every one
> of them, for a field the job had stopped requiring in between. The
> operator asked for a new customer type, was offered one, and got the
> old question back under the offer. There is no answer that ends it
> except naming a value nobody needs, and no reason to.
>
> So the job's own declaration is read again here rather than trusted
> from when the question was written. It can only ever REMOVE names: a
> question is still a question about the job it named, and a field that
> has since become required is one the run will ask for itself.
>
> One read, and only where a question is standing. A thread with nothing
> waiting pays nothing.

## `Converse._question_stands`, [line 330](../../../../../../../backend/src/sro/application/chat/converse.py#L330): Docstring

> Whether a question is standing NOW, rather than when this request
> began.
>
> `execute` reads the thread once, at the top, and everything after that
> is a model call: the reading, the placement, the resolver. Seconds. And
> the question this door would talk over is written by somebody else --
> `RunWorkflow._ask_for_values` (`workflow_runs.py:589`), from a task the
> start-run route spawned and never awaited (`routers/workflow_runs.py:
> 139`), after a whole live browser run has tried and failed to find the
> values. Two independent transactions on one thread, no lock between
> them.
>
> Measured on the deployment 2026-09-22 at 01:06. The operator asked for
> a customer type, the run went to look in their mail, and they typed
> `i will type` while it was looking. This door had read the thread
> before the run's question was committed, so `pending_job` saw a job
> offer rather than a question, `standing` was false, and the guard below
> never fired: *"Nobody has demonstrated that, so I would work it out on
> the screen: i will type"*, and five Configuration menus. The question
> landed a moment later and was buried under them -- which is why the
> stored thread has the question at 20 and the plan at 22.
>
> So the freshest possible read, at the last possible moment, and only on
> the path that is about to say the one thing worth not saying. It does
> not close the window -- an operator who types before the run has asked
> anything still meets a thread with no question in it -- and that
> remainder is the run's own flight, not this read. What it does close is
> every case where the question was already written by the time this door
> decided, which is the case that was measured.

## `Converse._also_said`, [line 335](../../../../../../../backend/src/sro/application/chat/converse.py#L335): Docstring

> Write down what they said, without acting on it.
>
> The sentence is theirs and it was said: a conversation that answers a
> person without showing what they asked reads, a minute later, as the
> system talking to itself.

## `Converse._ask_it_again`, [line 350](../../../../../../../backend/src/sro/application/chat/converse.py#L350): Docstring

> Put the standing question back, under whatever was just said.
>
> The same decision it was asked with, so the state rides along intact --
> what is established, what is still missing, where the run had got to.
> A question re-asked with a thinner decision than the one it replaces is
> a question that loses an answer somebody already gave.

## `Converse._is_it_an_answer`, [line 386](../../../../../../../backend/src/sro/application/chat/converse.py#L386): Docstring

> The value to take, or None where that sentence was not an answer.
>
> Never None where nothing could read it. A deployment with no model, a
> reading that raised, a cap spent -- all of them behave as this door
> behaved before the reading existed, because a panel that quietly stops
> accepting answers when a model is unreachable is worse than one that
> takes too many.
>
> `let_go` first and without asking anybody: "no" and "never mind" end
> the question, and a reading asked whether "no" answers "what should
> Customer Type be" has been given a question with no good answer.

## `Converse._answer_the_question`, [line 406](../../../../../../../backend/src/sro/application/chat/converse.py#L406): Docstring

> Take that sentence as the value it was asked for, and go on.
>
> Three ends, and the whole state of it lives on the decision each one
> writes -- not in a session, not on a row. An operator answering two
> questions over five minutes does not depend on a process staying up,
> and a second browser reading the thread sees the same thing.
>
> **Called off.** "No", "never mind": said whole, never by substring, so
> a description reading "leave it in receiving" is a description.
>
> **One down, more to go.** The answer goes in, the next question comes
> out, and the decision carries what is established so far.
>
> **The last one.** No more questions: the job is said back as a `job`
> decision with nothing missing and `resume`, which is the panel's cue to
> start it without asking again. They already said yes; asking twice for
> the same permission is how a system teaches somebody to stop reading
> what it asks.

## `Converse._say_yes_to_it`, [line 505](../../../../../../../backend/src/sro/application/chat/converse.py#L505): Docstring

> Start the job that was just offered, or ask for what it still needs.
>
> Two ends, and which one is decided by whether anything can go and look.
> A deployment that can read the operator's mail starts the job and lets
> the run find the rest -- that is what the card's own Yes does, and a
> conversation that demanded values the card would not is two answers to
> one question. A deployment that cannot asks here, one value at a time,
> and `_answer_the_question` takes it from there.

## `Converse._placed_by_the_rig`, [line 571](../../../../../../../backend/src/sro/application/chat/converse.py#L571): Docstring

> Which mined job this sentence is about, or None to ask the skills.
>
> None on every refusal as well as on a sentence the rig cannot place:
> no model configured, the day's cap spent, a door that raised. The
> conversation still happens -- it happens the way it did before this
> existed, which is the behaviour the console has always had.

## `Converse._say_the_job`, [line 581](../../../../../../../backend/src/sro/application/chat/converse.py#L581): Docstring

> The rig's answer, in the thread, with what a press would need.

## `Converse._ask_which`, [line 656](../../../../../../../backend/src/sro/application/chat/converse.py#L656): Docstring

> A question with the jobs it was choosing between, and no press.
>
> `kind: "which_job"` and deliberately not `"job"`: the browser builds an
> offer out of a job decision, and a decision it cannot act on must not
> look like one it can.

## `Converse.matched`, [line 694](../../../../../../../backend/src/sro/application/chat/converse.py#L694): Docstring

> A watched mailbox recognised a task. Said once, by name.
>
> A skill or a mined job: `named` is what the person reads and the two
> ids say which kind it was, because the press that follows goes to a
> different door for each. One method rather than two -- the sentence,
> the once-per-offer rule and the "names, never values" rule are the same
> for both, and a second copy of them is two that drift.
>
> The operator has to see this somewhere that survives the panel closing,
> which is the thread. What must not follow it there are the values: they
> were read out of somebody's mail, and `ValueAt` exists so they stay in
> the browser that read them. So the message carries which names were
> read and not what they said. The browser still holds the values, and
> the press that starts a run carries them then.
>
> Once per offer. A browser reports a match per frame it sees the mail in,
> and a conversation that says the same sentence four times is one nobody
> reads. Recognised by the offer id the browser minted -- absent from an
> older extension, which is why nothing is written without one: there
> would be no way to tell the second report from the first.

## `Converse._said_to_a_run`, [line 735](../../../../../../../backend/src/sro/application/chat/converse.py#L735): Docstring

> Something said to a run that is happening, rather than a request.
>
> Not `note` above, which is this class's other way of writing into a
> thread: that one is the system reporting a pursuit that finished in the
> background, and this one is the operator talking. Two methods of one
> name meaning opposite halves of an exchange is a trap for whoever reads
> them next.
>
> Kept and not resolved. An operator watching a run who types "use the
> north yard address" is talking about the thing in front of them; putting
> that sentence through intent matching finds some other skill and offers
> to run it, which is the opposite of what they meant.
>
> Nothing acts on it yet. It is recorded against the run so it is in the
> transcript beside the step it arrived during, and so the surface can say
> honestly that it was heard -- what reads it is the planner, when there
> is one. A note that silently changed a run would be worse than one that
> does nothing: changing the values a run uses is `Run.revise`'s job, where
> the change is checked against the names the skill declares.

## `Converse.started`, [line 753](../../../../../../../backend/src/sro/application/chat/converse.py#L753): Docstring

> Put a run into the conversation the moment it starts.
>
> Before, the message was written when the run finished, so a task that
> takes twelve seconds left the operator with a spinner and a card that
> forgot what it was doing. The message is the anchor: the console
> streams the steps into it as they land, and it is already in the
> transcript if the browser is closed halfway.

## `Converse.performed`, [line 790](../../../../../../../backend/src/sro/application/chat/converse.py#L790): Docstring

> Write a run the operator started into the conversation that asked for it.
>
> Until now a run started from a card lived in the console's memory: it
> survived nothing -- a re-render put the empty form back, and a reload
> lost the fact that anything had happened at all. A run belongs in the
> transcript for the same reason every other decision does. Somebody
> reading this thread tomorrow needs to see that a supplier was created,
> by whom, and what came back.

## `Converse._narrowed`, [line 830](../../../../../../../backend/src/sro/application/chat/converse.py#L830): Docstring

> The question that was actually asked, where the taught skill answers
> a wider one.
>
> "Show me supplier TESTSUPPLIERSRO" matched the read that lists every
> supplier, and replaying it returned all two hundred and thirty-nine --
> the one word that said which supplier was dropped on the floor. Here
> the field dictionary says what that value is called, the taught call
> proves the filter dialect, and the request is composed from both.

## `Converse._next_steps`, [line 862](../../../../../../../backend/src/sro/application/chat/converse.py#L862): Docstring

> What can be asked next, from what this answer actually contains.

## `Converse._write_down`, [line 890](../../../../../../../backend/src/sro/application/chat/converse.py#L890): Docstring

> Keep the question, so answering it once teaches it for everybody.
>
> The next person to ask about "parcel" gets a narrowed read rather than
> the same question, because what an operator says a word means is
> knowledge like anything else here.

## `Converse._look_it_up`, [line 904](../../../../../../../backend/src/sro/application/chat/converse.py#L904): Docstring

> The lookup door's answer to this question, or None if it is not one.
>
> None on every path that is not "a question with no skill behind it":
> a sentence that asks for work, a question a taught skill matched, a
> deployment with no lookup services, a plan that came back unready.
> Each of those falls through to what this door did before, which is
> still the right answer for them.

## `Converse._say_what_was_found`, [line 920](../../../../../../../backend/src/sro/application/chat/converse.py#L920): Docstring

> The answer, in the thread, carried as structure rather than prose.
>
> The panel already has the renderer: `result.js` reads a body, counts
> the records and draws the first few in a table. What it could not do
> was reach one -- a lookup's answer arrived only through `/v1/ask`, into
> a card beside the conversation, while the conversation itself carried
> the screen walk. So the decision carries the same shape that card is
> built from and the thread draws it the same way.

## `Converse._answer_now`, [line 951](../../../../../../../backend/src/sro/application/chat/converse.py#L951): Docstring

> Run a read the moment it is asked for, and answer with what came back.

## `Converse.__init__`, [line 104](../../../../../../../backend/src/sro/application/chat/converse.py#L104): Comment

Code: `self._answers = answers`

> Whether a sentence typed while a question stands is the answer to it.
> Optional: a deployment without one takes every sentence, exactly as
> this door did before the reading existed.

## `Converse.__init__`, [line 112](../../../../../../../backend/src/sro/application/chat/converse.py#L112): Comment

Code: `self._can_gather = can_gather`

> Whether a run of a mined job can go and find a value nobody typed.
>
> What the card asks for, and it is the difference between a person
> being asked to type a code out of a mail they have open and a run
> reading it themselves. Told to the panel rather than decided there:
> the connector is a deployment's, and a browser cannot know whether
> this one has a mailbox it may read.

## `Converse.__init__`, [line 113](../../../../../../../backend/src/sro/application/chat/converse.py#L113): Comment

Code: `self._plan_lookups = plan_lookups`

> The door that owns a question.
>
> `/v1/ask` has always decided which of the two worlds a sentence
> belongs to -- an instruction for the jobs, a question for the
> lookups -- and this door never asked. So a question nothing was
> taught for came back here as a PROPOSAL to open five screens and
> work it out, seven seconds before the lookup door answered it
> properly from an endpoint. Two answers on screen to one sentence,
> and the wrong one first.
>
> Optional, like every other model-backed service here: a deployment
> without one behaves exactly as this door did before.

## `Converse.execute`, [line 143](../../../../../../../backend/src/sro/application/chat/converse.py#L143): Comment

Code: `async with self._uow as uow:`

> A question this conversation asked is answered by the next thing
> said in it, before anything tries to read that sentence as a fresh
> request.
>
> "GPP" placed against the jobs is a sentence about nothing. Against
> the question that was actually asked -- *what should Customer Type
> be?* -- it is the answer, and reading it any other way is how a
> system asks somebody a question and then ignores what they say. It
> also saves the model call: the reading that matters already happened
> when the job was placed.

## `Converse.execute`, [line 157](../../../../../../../backend/src/sro/application/chat/converse.py#L157): Comment

Code: `answered_it, about = await self._is_it_an_answer(ctx, waiting, text)`

> And only if it IS one. A question standing here used to take
> whatever was typed next, which is right for `GU9` and wrong for
> everything else somebody types while they wait -- and what they
> type while waiting is usually about the waiting.
>
> Measured on the deployment 2026-09-18: the operator had sent the
> answer by mail and typed `has reply arrived` to ask this system
> whether it had landed. It was taken as the value, a run started a
> millisecond later, and `HAS REPLY ARRIVED` went into a
> four-character box in a live warehouse system.
>
> A sentence that is not an answer falls through to everything
> below and is treated as what it is. The question is not consumed,
> so it is still standing when they do answer it.

## `Converse.execute`, [line 167](../../../../../../../backend/src/sro/application/chat/converse.py#L167): Comment

Code: `if about != "another_task":`

> About the waiting, which is what a person who is waiting asks
> about. Answered here and not handed on.
>
> `check now` went to the task resolver, which is a door for "what
> work do you want done" -- so it planned one, and answered two
> words about a mailbox with a wall of text about Check In and
> Check Out screens nobody had mentioned. Seen on the deployment
> 2026-09-18, 16:42.

## `Converse.execute`, [line 172](../../../../../../../backend/src/sro/application/chat/converse.py#L172): Comment

Code: `placed = await self._placed_by_the_rig(ctx, text)`

> And only where the jobs agree that it IS one.
>
> `another_task` is a model's reading of a sentence, and the
> sentence that named this was `i wll type` -- the operator saying
> they would type the value, in answer to a question asking for
> it. Read as a request for different work, it went to the door
> that proposes work: "Nobody has demonstrated that, so I would
> work it out on the screen: i wll type", and five Configuration
> menus nobody had mentioned. Measured on the deployment
> 2026-09-21 at 17:10, in an operator's own conversation.
>
> The reading was wrong and no wording will make it always right.
>
> Refusing to carry on at all is not the answer either. Whether a
> sentence is a request for different work cannot be decided from
> the sentence -- "create an equipment type instead" places against
> nothing on a tenant that has never demonstrated one, and it is
> still a request. The door's own test says so: *somebody who says
> "create an equipment type instead" has asked for work, and a door
> that replied "I am still waiting on Customer Type" to that would
> be the old swallowing with better manners*.
>
> What CAN be decided is whether there is anything to say. The harm
> measured was not the carrying on; it was the PROPOSAL -- a door
> with no taught skill, no lookup and no read still answering, out
> of a plan it made from the screen. So the sentence is carried on
> with (`standing`), and where all this door has for it is a plan
> made up on the spot, it says nothing and the standing question is
> what the operator sees.
>
> The placement is handed down, so this costs no extra model call
> on the path that does turn out to be another task.

## `Converse.execute`, [line 173](../../../../../../../backend/src/sro/application/chat/converse.py#L173): Comment

Code: `await self._carry_on(`

> Said, answered, and then asked again.
>
> The asking again is not politeness. `pending_job` reads the LAST
> thing the assistant decided, so an ordinary reply written under a
> standing question buries it -- the sentence gets its answer and
> the question is gone, which is the same swallowing by a longer
> road. Repeating it is also what a person does: they answer what
> they were asked, and then say what they are still waiting for.

## `Converse._carry_on`, [line 229](../../../../../../../backend/src/sro/application/chat/converse.py#L229): Comment

Code: `offered = offered_job(said_before, answering)`

> And a job this conversation has just offered, agreed to.
>
> Measured on the deployment, 2026-09-17 at 03:17. The assistant said
> "Create a Customer Type does that -- say the word and I will run it",
> the operator said "pls do", and the reply was "Nothing has been
> taught for that": the sentence went to the resolver below, which
> ranks this tenant's taught SKILLS and had never heard of it. Nothing
> was holding on to what had just been offered.
>
> A system that asks for a word and then does not know the word is the
> same fault as the boxes on the offer card: it asks, and then ignores
> the answer.

## `Converse._carry_on`, [line 247](../../../../../../../backend/src/sro/application/chat/converse.py#L247): Comment

Code: `if isinstance(placed, _NotAsked):`

> The rig's jobs first, and where they place the sentence, only them.
>
> An operator typed "lets create warehouse equipment type" at a browser
> whose rig holds exactly that job, and was answered "Create a customer
> type does that. I still need long_description." The resolver below
> ranks the tenant's taught SKILLS -- seven of them, none about
> equipment types -- so it answered with the nearest thing it had. The
> right job was in the rig all along and this door never asked it.
>
> One model call and not two: the reading that answers here is the
> reading the panel's offer is built from, rather than this door
> spending one on the skills library and the browser spending another
> on the jobs.
> Asked here, unless the caller has already asked. A sentence typed
> under a standing question is placed against the jobs BEFORE the
> question is abandoned, and asking a second time would be a second
> model call for an answer this already has.

## `Converse._carry_on`, [line 258](../../../../../../../backend/src/sro/application/chat/converse.py#L258): Comment

Code: `parameters={**_gathered(thread, _awaiting(thread)), **(parameters or {})},`

> Values already given for the skill under discussion. An operator
> who answers one question at a time should not lose the first
> answer when they give the second.

## `Converse._carry_on`, [line 259](../../../../../../../backend/src/sro/application/chat/converse.py#L259): Comment

Code: `after=_last_asked(thread),`

> What was being talked about a moment ago. A conversation whose
> every sentence is resolved alone is not a conversation.

## `Converse._carry_on`, [line 263](../../../../../../../backend/src/sro/application/chat/converse.py#L263): Comment

Code: `looked = await self._look_it_up(ctx, text, resolution)`

> A question nothing was taught for belongs to the lookup door.
>
> The taught path below still comes first -- a skill that knows which
> call answers a question is a better answer than a plan made from the
> knowledge base. This is the case where there is no such skill, and
> where this door used to answer with a PROPOSAL: "Nobody has
> demonstrated reading that, so I will work it out on the screen",
> followed by five screens to open.
>
> Measured on the deployment 2026-09-21. Asked "is there a customer
> type called KKYT", three doors answered one sentence:
>
>   18:30:26  POST /v1/lookups            3601ms
>   18:30:35  POST /v1/threads/../messages 7691ms  <- the screen walk
>   18:30:43  POST /v1/ask                 6567ms  <- the answer
>
> The wrong one arrived first and read as final. The lookup planned
> `call /data/WM/wm/customerTypes`, got 200, and found KKYT -- which
> this door proposed to go and read off a screen instead.
>
> `is_a_question` is the same word rule `/v1/ask` decides by, with no
> model, so the two doors cannot disagree about what a question is.

## `Converse._carry_on`, [line 267](../../../../../../../backend/src/sro/application/chat/converse.py#L267): Comment

Code: `narrowed = await self._narrowed(ctx, resolution)`

> A question is answered from the system, now. The taught skill knows
> which call answers it; what it saw when it was taught is a description
> of that afternoon, and showing it as though it were current is how a
> console tells somebody there are sixteen when there are twenty-three.
>
> Only reads, and only when nothing is missing. A write still waits for
> the operator to say go -- that confirmation is what an assisted run
> records as its authorisation, and it is not ours to assume.
> The narrower question first, where the sentence asked one: replaying
> a taught read that answers something wider is how "show me supplier
> X" came back as every supplier there is.

## `Converse._carry_on`, [line 268](../../../../../../../backend/src/sro/application/chat/converse.py#L268): Comment

Code: `run = None if narrowed else await self._answer_now(ctx, resolution)`

> A question of our own stops the wider read too: answering something
> nobody asked, because the thing they did ask could not be placed, is
> the confident wrong answer wearing a table.

## `Converse._carry_on`, [line 270](../../../../../../../backend/src/sro/application/chat/converse.py#L270): Comment

Code: `if resolution.proposal is not None and (`

> A plan made up on the screen, under a question of ours that is still
> standing. This is the one thing this door says that is worth not
> saying: "Nobody has demonstrated that, so I would work it out on the
> screen: i wll type", and five Configuration menus nobody mentioned.
>
> Only the PROPOSAL. A taught skill still answers, a lookup still
> answers, and so does "Nothing has been taught for that" -- somebody
> who asks for work this tenant has never demonstrated is owed that
> sentence, not a second copy of the question they are already looking
> at. What they are not owed is a plan this door invented because it
> had nothing.

## `Converse._still_wanted`, [line 315](../../../../../../../backend/src/sro/application/chat/converse.py#L315): Comment

Code: `if job is None or not job.parameters:`

> A job that declares nothing has said nothing, which is not the same
> as saying nothing is required. A parameter is learnt from two doings
> that varied a field, so a job done once declares none at all -- and
> dropping its questions on that basis would silence every question a
> young job ever asks.

## `Converse._still_wanted`, [line 328](../../../../../../../backend/src/sro/application/chat/converse.py#L328): Comment

Code: `return replace(waiting, missing=still) if still else None`

> Nothing left to ask. The question is over, and the sentence under it
> is an ordinary sentence rather than an answer to something nobody
> needs.

## `Converse._is_it_an_answer`, [line 391](../../../../../../../backend/src/sro/application/chat/converse.py#L391): Comment

Code: `named = said_as_the_value(pending, text)`

> Named by the person themselves, and nothing needs to be read.
>
> This is the way out of the loop. The reading is told to refuse when
> it is unsure, which is the right default and leaves an operator who
> typed a real value with no move except typing it again -- so the
> re-ask below tells them this form exists, and this takes it.

## `Converse._is_it_an_answer`, [line 404](../../../../../../../backend/src/sro/application/chat/converse.py#L404): Comment

Code: `return None, read.about`

> Could not tell is its own thing, not a reading that said `another_task`.
> `read.answers` is `None` on every path nothing could actually read -- no
> model, a call that raised, a reply with nothing in it -- and `read.about`
> is `""` on every one of them, which `if about != "another_task":` in
> `execute` reads as `the_wait` does: re-ask under the standing question,
> never carry on as though a sentence had been placed against the jobs.
> Taking the unreadable sentence as the value is how `HAS REPLY ARRIVED`
> reached a four-character box; this is the same question asked in
> reverse, at the door that decides what a refusal means.

## `Converse._answer_the_question`, [line 447](../../../../../../../backend/src/sro/application/chat/converse.py#L447): Comment

Code: `refused = too_long_for(pending, text)`

> An answer the box will not hold leaves the question standing,
> and saying so is the whole difference between a loop somebody
> can get out of and one they cannot. Silently re-asking the
> same question reads as a system that ignored them.

## `Converse._answer_the_question`, [line 459](../../../../../../../backend/src/sro/application/chat/converse.py#L459): Comment

Code: `"from_step": filled.from_step,`

> Where the run that asked had got to. Without it
> the answer starts the job from the beginning and
> re-walks every step the first run performed, to
> arrive back at the box it stopped in front of.

## `Converse._answer_the_question`, [line 460](../../../../../../../backend/src/sro/application/chat/converse.py#L460): Comment

Code: `"mail_thread": filled.mail_thread,`

> So the run this answer starts answers to the same
> mail a run the card started would have.

## `Converse._answer_the_question`, [line 462](../../../../../../../backend/src/sro/application/chat/converse.py#L462): Comment

Code: `"resume": True,`

> They already pressed yes. This is the same press
> arriving late, not a second one to ask for.

## `Converse._say_yes_to_it`, [line 555](../../../../../../../backend/src/sro/application/chat/converse.py#L555): Comment

Code: `decision["resume"] = True`

> The press, arriving as a sentence. `resume` is what tells the
> panel this is the yes and not another offer to answer.

## `Converse._say_the_job`, [line 588](../../../../../../../backend/src/sro/application/chat/converse.py#L588): Comment

Code: `if not placed.sure:`

> Not sure which job: ask, rather than start one.
>
> The reading is still the best one it had, and it is offered
> first -- but as a question with the others beside it, and with no
> `workflow_id` for a press to act on. A guess that creates one
> wrong record is a nuisance; the same guess against a list of
> twenty is twenty wrong records in a warehouse, and the cost of
> asking is one sentence.

## `Converse._say_the_job`, [line 600](../../../../../../../backend/src/sro/application/chat/converse.py#L600): Comment

Code: `said = (`

> The run goes and looks. Said as what will happen rather than
> as a demand, because the demand was the old behaviour and it
> put a person in front of four boxes -- two of them the body
> keys a form posts, which nobody has ever typed -- for values
> sitting in the mail that asked for the job.

## `Converse._say_the_job`, [line 635](../../../../../../../backend/src/sro/application/chat/converse.py#L635): Comment

Code: `decision={`

> The structured half, which is what a press is built from:
> the browser makes its offer out of this rather than
> spending a second reading of the same sentence.

## `Converse._say_the_job`, [line 648](../../../../../../../backend/src/sro/application/chat/converse.py#L648): Comment

Code: `"can_find": self._can_gather,`

> Whether the missing ones are a demand or a plan. The
> panel draws its boxes off this: required where
> nothing can go and look, optional where something
> can, and a blank that reaches the door is refused as
> a typed blank either way.

## `Converse._ask_which`, [line 686](../../../../../../../backend/src/sro/application/chat/converse.py#L686): Comment

Code: `"titles": titles,`

> The names, because the question is asked of a person:
> a panel drawing two buttons reading `wfl_c79d02bb`
> asks nobody anything.

## `Converse.matched`, [line 727](../../../../../../../backend/src/sro/application/chat/converse.py#L727): Comment

Code: `"missing": list(missing),`

> Where nothing can go and look, this is what the card
> says it cannot run without. Where something can, the
> names are still said -- a person reading the thread
> should know which values the mail did not carry --
> and `can_find` is what decides whether the button is
> a demand or a plan.

## `Converse.performed`, [line 808](../../../../../../../backend/src/sro/application/chat/converse.py#L808): Comment

Code: `"next": ("open" if any(step.unreachable for step in run.steps) else "ask")`

> The one thing that would help, for a surface that
> shows a failure as a sentence and a single button.
> A step nothing could reach is a page to open; every
> other failure is somebody's to look at.

## `Converse._narrowed`, [line 846](../../../../../../../backend/src/sro/application/chat/converse.py#L846): Comment

Code: `verb=resolution.verb,`

> The verb is what they want done, not a value to filter by:
> "count the addresses" asked which field the word "count" names,
> because two fields are called Count something.

## `Converse._narrowed`, [line 851](../../../../../../../backend/src/sro/application/chat/converse.py#L851): Comment

Code: `if narrowed.options:`

> Only a real choice becomes a question. A statement that this read
> cannot answer the sentence is not something to ask anybody.

## `Converse._narrowed`, [line 858](../../../../../../../backend/src/sro/application/chat/converse.py#L858): Comment

Code: `logger.info("the narrowed read did not answer: %s", asked.detail)`

> The narrowing was right and the request did not work -- an
> expired session, an endpoint that answered nothing. Falling back
> to the taught read answers a wider question, but answering
> nothing at all because a composed request failed is worse.

## `Converse._look_it_up`, [line 908](../../../../../../../backend/src/sro/application/chat/converse.py#L908): Comment

Code: `return None`

> Nothing here knows how to look it up, which is the case the
> proposal below is genuinely for: it says what the knowledge base
> has and offers to work the screen out once.

## `Converse._look_it_up`, [line 918](../../../../../../../backend/src/sro/application/chat/converse.py#L918): Comment

Code: `return await self._run_lookups.execute(ctx, plan=planned.plan, within=K_WHILE_TALKING)`

> `K_WHILE_TALKING`, not the lookup door's own budget. A reply in a
> panel is a turn in a conversation, and a turn that takes a minute has
> stopped being one: measured on the deployment 2026-09-21, request
> `req_10d3ff9b`, the browser's socket dropped twice inside one
> request, a command waited out the full 45 seconds, and the reply took
> 67459ms. Routing the conversation through this door is what made a
> thread reply wait on a browser at all; this is what stops it waiting
> on one that is not answering.

## `Converse._answer_now`, [line 970](../../../../../../../backend/src/sro/application/chat/converse.py#L970): Comment

Code: `logger.info("could not answer from the system: %s", refusal)`

> A refused read is worth saying out loud, and worth saying in the
> reply rather than as an empty answer: the breaker being open is a
> fact about the system, not an absence of transport modes.

## `_reply`, [line 1009](../../../../../../../backend/src/sro/application/chat/converse.py#L1009): Comment

Code: `wanted = ", ".join(resolution.missing_parameters)`

> Values were read, but not all of them. Telling somebody to "say
> go" when the run cannot start is how a system trains people to
> ignore what it says.

## `_decision`, [line 1091](../../../../../../../backend/src/sro/application/chat/converse.py#L1091): Comment

Code: `"items": [dict(item) for item in resolution.items],`

> The table the operator confirms. Rendered rather than acted on: their
> confirmation is what an assisted run records as its authorisation.

## `_decision`, [line 1093](../../../../../../../backend/src/sro/application/chat/converse.py#L1093): Comment

Code: `"suggestions": list(suggestions),`

> Earned from this answer's own columns and the skills taught for this
> entity. Never a fixed list: the console used to offer "which X are
> used for parcel" under every result in the system.

## `_decision`, [line 1096](../../../../../../../backend/src/sro/application/chat/converse.py#L1096): Comment

Code: `"run_id": run.id.value if run else None,`

> The answer, from the system, at the moment it was asked.

## `_decision`, [line 1097](../../../../../../../backend/src/sro/application/chat/converse.py#L1097): Comment

Code: `"matched_skill_name": resolution.matched.skill.name if resolution.matched else None,`

> The name, not only the id: a sidebar reading "ran skl_a6f7b33c" tells
> nobody anything.

## `_what_was_found`, [line 1147](../../../../../../../backend/src/sro/application/chat/converse.py#L1147): Comment

Code: `if any(_ran_out(one.detail) for one in found.looked):`

> Name the browser where the browser is what did not answer. "I could
> not read that. timeout" is a sentence about this system's plumbing;
> the person reading it can see their own browser and can do something
> about it.

## `_what_was_found`, [line 1150](../../../../../../../backend/src/sro/application/chat/converse.py#L1150): Comment

Code: `said = [`

> The reader's own sentence, where it read records.
>
> `Answer.sentence` is deterministic -- counted and named from the payload,
> never summarised by a model, because "16" has to be 16 -- and it is the
> line somebody asking a question wanted instead of a table. "Read from
> /data/WM/wm/customerTypes" was this door describing its own plumbing.

## `Converse._say_yes_to_it`, [line 548](../../../../../../../backend/src/sro/application/chat/converse.py#L548): Note

Code: `said = f"Left {offered.title}."`

> "No" to an offered job leaves it, as it drops a standing question: the
> offer stops standing and nothing runs. Without it the word went to the
> resolver as a request of its own.

## `Converse.execute`, [line 151](../../../../../../../backend/src/sro/application/chat/converse.py#L151): Note

Code: `and offered_job(said_before, answering) is None`

> An answer pressed under a question that is no longer open, or that is not a
> question at all, is refused with a reply and nothing else. It never falls
> through to the resolver or to another offer.

## `K_CLOSED`, [line 53](../../../../../../../backend/src/sro/application/chat/converse.py#L53): Note

Code: `K_CLOSED = "That question is no longer open, so nothing was done."`

> Said with no decision, so the refusal does not itself become the newest
> decision a typed sentence would be read against.

## `Converse.execute`, [line 146](../../../../../../../backend/src/sro/application/chat/converse.py#L146): Note

Code: `if answering is not None and before.opened_by != ctx.principal_id:`

> A press acts only on a question asked of the operator pressing it. Threads
> are readable across the tenant, and a should-we question carries the
> operator's own mail to colleagues; a colleague who can see it cannot answer
> it.

## `Converse._say_yes_to_it`, [line 519](../../../../../../../backend/src/sro/application/chat/converse.py#L519): Note

Code: `if still is None or still.id != asked:`

> The compare-and-set. The question was found open in one transaction and is
> answered in another; under the thread's row lock this checks it is still the
> open one before writing, so of two presses (or a press and a typed yes)
> exactly one answers and the other is told it is no longer open. The same
> check guards `_answer_the_question`.

## `Converse._say_yes_to_it`, [line 544](../../../../../../../backend/src/sro/application/chat/converse.py#L544): Note

Code: `"offer": str((still.decision or {}).get("offer") or asked.value),`

> The offer this yes answers rides on the `resume` decision to the browser,
> which starts the run with it as `offer`, so the store refuses a second run
> of it however the second start arrives. A question about a mail carries the
> mail as its offer (`mail:{id}`), so a mail read again after a crash, whose
> run already started, is refused its second run; any other question is its
> own offer.

## `Converse._carry_on`, [line 245](../../../../../../../backend/src/sro/application/chat/converse.py#L245): Note

Code: `said=f"Say yes to run {offered.title}, or no to leave it.",`

> Words pressed under an open should-we question that are neither yes nor no
> ask for one again. They never fall through to be read as a new request.

## `Converse._say_the_job`, [line 599](../../../../../../../backend/src/sro/application/chat/converse.py#L599): Comment

Code: `if placed.cannot_run:`

> A job that cannot run is named with its reasons, as a note and not a job card
> whose press the start would refuse. Never "no such job".
