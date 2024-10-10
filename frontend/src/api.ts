import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { API_BASE_PATH } from "./const";
import {
  Service,
  FullFlow,
  Signature,
  TickInfo,
  Flow,
  FlowsQuery,
} from "./types";

const defaultFlowsQuery: FlowsQuery = {
  includeTags: [],
  excludeTags: [],
  service: "",
  tags: [],
  flags: [],
  flagids: [],
  // Add other default properties as needed
};

export const tulipApi = createApi({
  reducerPath: 'tulipApi',
  baseQuery: fetchBaseQuery({ baseUrl: API_BASE_PATH }),
  tagTypes: ['Flow', 'Service', 'Tag'],
  endpoints: (builder) => ({
    getServices: builder.query<Service[], void>({
      query: () => "/services",
      providesTags: ['Service'],
    }),
    getFlagRegex: builder.query<string, void>({
      query: () => "/flag_regex",
    }),
    getFlow: builder.query<FullFlow, string>({
      query: (id) => `/flow/${id}`,
      providesTags: (result, error, id) => [{ type: 'Flow', id }],
    }),
    getFlows: builder.query<Flow[], FlowsQuery>({
      query: (query) => ({
        url: `/query`,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...query,
          includeTags: query.includeTags.length > 0 ? query.includeTags : undefined,
          excludeTags: query.excludeTags.length > 0 ? query.excludeTags : undefined,
        }),
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ _id }) => ({ type: 'Flow' as const, id: _id.$oid })),
              { type: 'Flow', id: 'LIST' },
            ]
          : [{ type: 'Flow', id: 'LIST' }],
    }),
    getTags: builder.query<string[], void>({
      query: () => `/tags`,
      providesTags: ['Tag'],
    }),
    getTickInfo: builder.query<TickInfo, void>({
      query: () => `/tick_info`,
    }),
    getSignature: builder.query<Signature[], number>({
      query: (id) => `/signature/${id}`,
    }),
    toPwnTools: builder.query<string, string>({
      query: (id) => ({ 
        url: `/to_pwn/${id}`, 
        responseHandler: "text" 
      }),
    }),
    toSinglePythonRequest: builder.query<string, { body: string; id: string; tokenize: boolean }>({
      query: ({ body, id, tokenize }) => ({
        url: `/to_single_python_request`,
        method: "POST",
        params: { tokenize: tokenize ? "1" : "0", id },
        responseHandler: "text",
        headers: {
          "Content-Type": "text/plain;charset=UTF-8",
        },
        body,
      }),
    }),
    toFullPythonRequest: builder.query<string, string>({
      query: (id) => ({
        url: `/to_python_request/${id}`,
        responseHandler: "text",
      }),
    }),
  starFlow: builder.mutation<void, { id: string; star: boolean }>({
      query: ({ id, star }) => ({
        url: `/star/${id}/${star ? "1" : "0"}`,
        method: 'POST',
      }),
      invalidatesTags: (result, error, { id }) => [{ type: 'Flow', id }],
      async onQueryStarted({ id, star }, { dispatch, queryFulfilled }) {
        const patchResult = dispatch(
          tulipApi.util.updateQueryData('getFlows', defaultFlowsQuery, (draft) => {
            const flow = draft.find((flow) => flow._id.$oid === id);
            if (flow) {
              if (star) {
                flow.tags.push("starred");
              } else {
                flow.tags = flow.tags.filter((tag) => tag !== "starred");
              }
            }
          })
        );
        try {
          await queryFulfilled;
        } catch {
          patchResult.undo();
        }
      },
    }),
  }),
});

export const {
  useGetServicesQuery,
  useGetFlagRegexQuery,
  useGetFlowQuery,
  useGetFlowsQuery,
  useLazyGetFlowsQuery,
  useGetTagsQuery,
  useGetSignatureQuery,
  useGetTickInfoQuery,
  useLazyToPwnToolsQuery,
  useLazyToFullPythonRequestQuery,
  useToSinglePythonRequestQuery,
  useStarFlowMutation,
} = tulipApi;